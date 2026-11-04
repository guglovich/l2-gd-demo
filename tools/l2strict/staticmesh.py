#!/usr/bin/env python3
"""L2 StaticMesh -> glTF exporter (independent of UModel).

Layout was reverse-engineered from engine.dll (UStaticMesh::Serialize,
UPrimitive::Serialize, 0x103108c5 / 0x10311293) and verified against
Oren_DEV_S.usx / O_DE_MT_Btm (452 verts / 422 faces):

  after the property list:
    FBox    BoundingBox   (24 B: min.xyz max.xyz, UE (X,Y,Z))
    FSphere BoundingSphere(16 B: center.xyz, radius)
    FStaticMeshVertexStream: compact count, count*24 B (Pos 3f32 + Normal
      3f32, unit length), int Revision
    FRawColorStream (Colors) / FRawColorStream (Alpha): compact count,
      count*4 B, int Revision
    UVStreams: compact K, per stream: compact count, count*8 B (2 f32),
      int, int
    IndexStream1/2: compact count, count*u16, int Revision
  then L2 licensee data (TLazyArray Faces / kDOP ...) — not needed here.

glTF axis mapping (same as the UModel pipeline): (x, z, -y) m = UE/100.
"""
import json
import math
import os
import struct


class Reader:
    def __init__(self, data: bytes, pos: int = 0):
        self.d = data
        self.p = pos

    def u8(self) -> int:
        b = self.d[self.p]
        self.p += 1
        return b

    def i32(self) -> int:
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self) -> float:
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def compact(self) -> int:
        """UE compact index (1-3 bytes, little-endian, sign via 0x80)."""
        b = self.u8()
        negative = bool(b & 0x80)
        more = bool(b & 0x40)
        value = b & 0x3F
        shift = 6
        while more:
            b = self.u8()
            more = bool(b & 0x80)
            value |= (b & 0x7F) << shift
            shift += 7
        return -(value + 1) if negative else value

    def raw(self, n: int) -> bytes:
        r = self.d[self.p:self.p + n]
        self.p += n
        return r


def _valid_vertex(rec: bytes) -> bool:
    x, y, z, nx, ny, nz = struct.unpack("<6f", rec)
    if not all(abs(v) < 1.2e5 for v in (x, y, z)):
        return False
    if not all(abs(v) <= 1.001 for v in (nx, ny, nz)):
        return False
    return abs(nx * nx + ny * ny + nz * nz - 1.0) < 0.02


def _find_sections(data: bytes, bulk_start: int, bulk_end: int,
                   vert_count: int, index_count: int) -> list:
    """Locate the FStaticMeshSection table. Engine-verified (sub_1030a41b):
    FStaticMeshSection is 20 bytes — (i32 f4; u16 FirstIndex; u16
    FirstVertex; u16 LastVertex; u16 fE; u16 NumFaces; 6 B tail) — preceded
    by a compact count. Followed by the second BoundingBox. Validated
    against the vertex/index pools."""
    want_tris = index_count // 3
    best = None
    for off in range(bulk_start, bulk_end - 22):
        rr = Reader(data, off)
        cnt = rr.compact()
        if cnt <= 0 or cnt > 64:
            continue
        ok = True
        secs = []
        for _ in range(cnt):
            if rr.p + 20 > bulk_end:
                ok = False
                break
            vals = struct.unpack_from("<IHHHHHHH", data, rr.p)
            rr.p += 20
            f4, fi, fv, lv, fe, nf = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]
            if f4 != 0 or fi >= index_count or nf == 0:
                ok = False
                break
            if fv > lv or lv >= vert_count or fi + nf * 3 > index_count:
                ok = False
                break
            secs.append((fi, fv, lv, nf))
        if not ok or not secs:
            continue
        covered = sum(s[3] for s in secs)
        if covered == want_tris:
            return secs
        if best is None and covered > 0:
            best = secs
    return best or []


def parse_static_mesh(data: bytes, start: int, size: int) -> dict:
    """Parse one StaticMesh export. `start` must point at the BINARY bulk
    (i.e. AFTER the property list — serial_offset + props.end).
    Returns dict or raises."""
    r = Reader(data, start)
    bbox_min = struct.unpack_from("<3f", data, r.p)
    bbox_max = struct.unpack_from("<3f", data, r.p + 12)
    r.p += 24
    sphere = struct.unpack_from("<4f", data, r.p)
    r.p += 16

    # --- vertex stream: find the anchor [compact count][count*24 valid]
    anchor = None
    p = r.p
    limit = start + size - 452 * 24
    while p < limit:
        probe = Reader(data, p)
        cnt = probe.compact()
        if 0 < cnt < 200000:
            ok = all(
                _valid_vertex(data[probe.p + i * 24:probe.p + i * 24 + 24])
                for i in range(min(cnt, 4))
            )
            if ok and probe.p + cnt * 24 + 4 <= start + size:
                # tail sanity: after the stream comes an int (Revision)
                anchor = (p, probe.p, cnt)
                break
        p += 1
    if anchor is None:
        raise ValueError("vertex stream anchor not found")
    _, vpos, vcount = anchor
    verts = []
    for i in range(vcount):
        rec = data[vpos + i * 24:vpos + i * 24 + 24]
        x, y, z, nx, ny, nz = struct.unpack("<6f", rec)
        verts.append((x, y, z, nx, ny, nz))
    r = Reader(data, vpos + vcount * 24)
    vert_revision = r.i32()

    # --- color / alpha streams
    colors = []
    for _ in range(2):
        n = r.compact()
        if 0 < n < 200000 and r.p + n * 4 + 4 <= start + size:
            r.p += n * 4
        r.i32()  # revision

    # --- uv streams
    uvs = []
    k = r.compact()
    if 0 <= k < 64:
        for _ in range(k):
            n = r.compact()
            if n <= 0 or r.p + n * 8 > start + size:
                raise ValueError(f"bad uv stream count {n}")
            uvs.append([
                struct.unpack_from("<2f", data, r.p + i * 8)
                for i in range(n)
            ])
            r.p += n * 8
            r.i32()
            r.i32()
    else:
        raise ValueError(f"bad uv stream array count {k}")

    # --- index streams
    indices = []
    for _ in range(2):
        n = r.compact()
        if n <= 0 or n > 4_000_000 or r.p + n * 2 > start + size:
            break
        idx = struct.unpack_from(f"<{n}H", data, r.p)
        indices.append(idx)
        r.p += n * 2
        r.i32()  # revision
    render_idx = None
    for idx in indices:
        if idx and max(idx) < len(verts):
            render_idx = idx
            break
    if render_idx is None:
        raise ValueError("no render index stream referencing the vertex pool")

    sections = _find_sections(data, start + 40, min(start + 4096,
                              start + size), len(verts), len(render_idx))

    return {
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
        "sphere": sphere,
        "verts": verts,
        "uvs": uvs,
        "indices": render_idx,
        "sections": sections,
        "vertex_revision": vert_revision,
    }


def write_gltf(path: str, name: str, mesh: dict) -> None:
    """Write the parsed mesh as glTF (+bin) in Godot-ready axes/scale."""
    blob = bytearray()
    buffer_views = []
    accessors = []

    positions = []
    for x, y, z, *_ in mesh["verts"]:
        positions.extend([x * 0.01, z * 0.01, -y * 0.01])
    normals = []
    for *_, nx, ny, nz in mesh["verts"]:
        l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        normals.extend([nx / l, nz / l, -ny / l])
    uvs = mesh["uvs"][0] if mesh["uvs"] else [(0.0, 0.0)] * len(mesh["verts"])
    uv_flat = []
    for u, v in uvs:
        uv_flat.extend([u, 1.0 - v])

    def add_view(data: bytes) -> int:
        while len(blob) % 4:
            blob.append(0)
        buffer_views.append({
            "buffer": 0, "byteOffset": len(blob), "byteLength": len(data),
        })
        blob.extend(data)
        return len(buffer_views) - 1

    def add_acc(view: int, comp: int, count: int, kind: str,
                mn=None, mx=None) -> int:
        acc = {
            "bufferView": view, "componentType": comp,
            "count": count, "type": kind,
        }
        if mn is not None:
            acc["min"] = mn
            acc["max"] = mx
        accessors.append(acc)
        return len(accessors) - 1

    pb = struct.pack(f"<{len(positions)}f", *positions)
    pv = add_view(pb)
    pos_acc = add_acc(
        pv, 5126, len(mesh["verts"]), "VEC3",
        [min(positions[0::3]), min(positions[1::3]), min(positions[2::3])],
        [max(positions[0::3]), max(positions[1::3]), max(positions[2::3])],
    )
    nb = struct.pack(f"<{len(normals)}f", *normals)
    nv = add_view(nb)
    nrm_acc = add_acc(nv, 5126, len(mesh["verts"]), "VEC3")
    ub = struct.pack(f"<{len(uv_flat)}f", *uv_flat)
    uvv = add_view(ub)
    uv_acc = add_acc(uvv, 5126, len(mesh["verts"]), "VEC2")
    ib = struct.pack(f"<{len(mesh['indices'])}H", *mesh["indices"])
    iv = add_view(ib)
    idx_acc = add_acc(iv, 5123, len(mesh["indices"]), "SCALAR")

    # One primitive per section (world.gd maps textures per primitive).
    prims = []
    secs = mesh.get("sections") or [(0, 0, len(mesh["verts"]) - 1,
                                     len(mesh["indices"]) // 3)]
    used = 0
    for (fi, fv, lv, nf) in secs:
        sub = mesh["indices"][fi * 3:(fi + nf) * 3]
        if not sub:
            continue
        used += len(sub) // 3
        sb = struct.pack(f"<{len(sub)}H", *sub)
        sv = add_view(sb)
        s_acc = add_acc(sv, 5123, len(sub), "SCALAR")
        prims.append({
            "attributes": {
                "POSITION": pos_acc,
                "NORMAL": nrm_acc,
                "TEXCOORD_0": uv_acc,
            },
            "indices": s_acc,
            "material": len(prims),
            "mode": 4,
        })
    if not prims or used * 3 < len(mesh["indices"]):
        # fallback: single primitive with everything
        prims = [{
            "attributes": {
                "POSITION": pos_acc,
                "NORMAL": nrm_acc,
                "TEXCOORD_0": uv_acc,
            },
            "indices": idx_acc,
            "material": 0,
            "mode": 4,
        }]

    gltf = {
        "asset": {"version": "2.0", "generator": "l2strict staticmesh"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": prims}],
        "materials": [{
            "name": f"l2mat{i}",
            "pbrMetallicRoughness": {"baseColorFactor": [0.5, 0.5, 0.5, 1.0]},
            "doubleSided": True,
        } for i in range(max(1, len(prims)))],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"uri": name + ".bin", "byteLength": len(blob)}],
    }
    with open(path + ".gltf", "w") as fp:
        json.dump(gltf, fp)
    with open(path + ".bin", "wb") as fp:
        fp.write(bytes(blob))


def convert_export(pkg_path: str, out_dir: str, only: set | None = None) -> list:
    """Convert every StaticMesh export of a package to glTF. Returns names."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from l2strict.package import Package
    from l2strict.properties import read_object

    pkg = Package.from_file(pkg_path)
    os.makedirs(out_dir, exist_ok=True)
    done = []
    for i in range(pkg.export_count):
        if pkg.class_name_of_export(i) != "StaticMesh":
            continue
        e = pkg.exports[i]
        name = pkg.name(e.object_name)
        if only and name not in only:
            continue
        try:
            # property list first: the binary bulk starts after it
            obj = read_object(
                pkg.data[e.serial_offset:e.serial_offset + e.serial_size],
                pkg, context=name, has_stack=bool(e.object_flags & 0x02000000),
            )
            bulk = e.serial_offset + obj.end
            mesh = parse_static_mesh(pkg.data, bulk,
                                     e.serial_size - obj.end)
        except ValueError as ex:
            print(f"  {name}: SKIPPED ({ex})")
            continue
        write_gltf(os.path.join(out_dir, name), name, mesh)
        done.append(name)
    return done


if __name__ == "__main__":
    import sys
    pkg_path = sys.argv[1]
    out_dir = sys.argv[2]
    only = set(sys.argv[3:]) or None
    names = convert_export(pkg_path, out_dir, only)
    print(f"converted {len(names)} meshes -> {out_dir}")
