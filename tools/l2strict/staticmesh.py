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
                   want_faces: int) -> list:
    """Locate the FStaticMeshSection table: compact count followed by
    count x 14-B entries (i32 f4=0; u16 FirstIndex; FirstVertex;
    LastVertex; fE; NumFaces) — the standard UE2 layout. Oracle: the
    FirstIndex sequence is non-decreasing and consecutive sections chain
    (FI + NF*3 = next FI). Verified on Oren_DEV_S (Bridge: 18 sections,
    sum NF = 924 = the whole index pool)."""
    best = None
    for off in range(bulk_start, bulk_end - 16):
        rr = Reader(data, off)
        try:
            cnt = rr.compact()
        except IndexError:
            continue
        if cnt <= 0 or cnt > 64:
            continue
        ok = True
        secs = []
        prev_fi = -1
        for _ in range(cnt):
            if rr.p + 14 > bulk_end:
                ok = False
                break
            f4, fi, fv, lv, fe, nf = struct.unpack_from("<IHHHHH", data, rr.p)
            rr.p += 14
            if f4 != 0 or fi < prev_fi:
                ok = False
                break
            if nf == 0:
                # an empty section is legal (UModel skips it in the output)
                secs.append((fi, fv, lv, fe, nf))
                continue
            if fv > lv or lv >= 30000 or fi + nf * 3 > 30000:
                ok = False
                break
            prev_fi = fi
            secs.append((fi, fv, lv, fe, nf))
        if not ok or not secs:
            continue
        covered = sum(s[4] for s in secs)
        if covered == want_faces:
            return secs
        if best is None or covered > sum(s[4] for s in best):
            best = secs
    return best or []


def parse_static_mesh(data: bytes, start: int, size: int,
                      hint_verts: int = 0) -> dict:
    """Parse one L2 StaticMesh binary bulk (props already consumed).

    Anchor-based (format-proof): the vertex stream is located by its
    compact count (== the hint from the staged glTF) followed by count
    x 24 B records (pos + normal, the L2 normals have length 512);
    the color/alpha/UV streams share the same element count; the index
    streams are u16 pools; the sections are 14-B tables whose NumFaces
    sum x 3 == the index count.
    """
    d = data
    end = start + size

    def compact(p):
        b = d[p]
        more = b & 0x40
        neg = b & 0x80
        v = b & 0x3F
        sh = 6
        p += 1
        while more:
            b = d[p]
            more = b & 0x80
            v |= (b & 0x7F) << sh
            sh += 7
            p += 1
        return (-(v + 1) if neg else v), p

    def valid_rec(p, stride=24):
        x, y, z, nx, ny, nz = struct.unpack_from("<6f", d, p)
        if not all(abs(t) < 1.2e5 for t in (x, y, z)):
            return 0
        ln2 = nx * nx + ny * ny + nz * nz
        # L2 normals: unit length OR the engine's 512 scale
        if not (0.9 < ln2 < 1.1 or 250000 < ln2 < 275000):
            return 0
        if stride == 32:
            u, v = struct.unpack_from("<2f", d, p + 24)
            if abs(u) > 16 or abs(v) > 16:
                return 0
        return 1

    # --- locate the vertex stream by the hint count
    vstart = None
    vcount = hint_verts
    if vcount < 8:
        raise ValueError("no vertex hint — the staged glTF must exist")
    # the compact encoding of the hint count (the 0x40 more-bit only when
    # the value actually continues into the next byte)
    enc = []
    n = vcount
    b0 = n & 0x3F
    n >>= 6
    if n:
        b0 |= 0x40
    enc.append(b0)
    while n:
        nxt = n >> 7
        enc.append((n & 0x7F) | (0x80 if nxt else 0))
        n = nxt
    pat = bytes(enc)
    q = start
    vstride = 24
    while True:
        q = d.find(pat, q, end)
        if q < 0:
            break
        vs = q + len(pat)
        for stride in (24, 32):
            good = sum(1 for i in range(min(vcount, 64))
                       if valid_rec(vs + i * stride, stride))
            if good == min(vcount, 64):
                vstart = vs
                vstride = stride
                break
        if vstart is not None:
            break
        q += 1
    if vstart is None:
        raise ValueError("vertex stream anchor not found (packed-vertex "
                         "meshes are a known pending RE target)")
    verts = []
    for i in range(vcount):
        p = vstart + i * vstride
        x, y, z, nx, ny, nz = struct.unpack_from("<6f", d, p)
        l = (nx * nx + ny * ny + nz * nz) ** 0.5
        if l > 2.0:
            nx, ny, nz = nx / l, ny / l, nz / l
        verts.append((x, y, z, nx, ny, nz))
    r = vstart + vcount * vstride

    # --- the color / alpha / UV streams share the element count
    uvs = []
    p = r + 4  # revision
    for width in (4, 4, 8):
        p0 = p
        c = compact(p0)[0]
        if c != vcount:
            p = p0 + 1
            continue
        p = compact(p0)[1]
        if width == 8:
            uvs = [struct.unpack_from("<2f", d, p + i * 8) for i in range(c)]
        p += c * width
        p += 4  # revision
        p0 = p

    # --- index streams: compact count + u16 pool with values < vcount
    indices = []
    p = r
    while p < end - 4:
        c, p2 = compact(p)
        if 8 <= c <= 4_000_000 and p2 + c * 2 + 4 <= end:
            pool = struct.unpack_from(f"<{c}H", d, p2)
            if max(pool) < vcount:
                indices.append(pool)
                p = p2 + c * 2 + 4
                continue
        p += 1
    render_idx = None
    for idx in indices:
        if idx and max(idx) < vcount:
            render_idx = idx
            break
    if render_idx is None:
        raise ValueError("no render index stream referencing the vertex pool")

    # --- sections: 14-B entries, oracle sum(NumFaces)*3 == index count
    sections = []
    idx_total = len(render_idx)
    best = None
    for off in range(start, min(vstart, start + 4096) - 16):
        cc, p2 = compact(off)
        if cc <= 0 or cc > 64:
            continue
        ok = True
        secs = []
        prev_fi = -1
        for _ in range(cc):
            if p2 + 14 > end:
                ok = False
                break
            f4, fi, fv, lv, fe, nf = struct.unpack_from("<IHHHHH", d, p2)
            p2 += 14
            if f4 != 0 or fi < prev_fi or fi + nf * 3 > idx_total:
                ok = False
                break
            if nf and (fv > lv or lv >= vcount):
                ok = False
                break
            prev_fi = fi
            secs.append((fi, fv, lv, fe, nf))
        if not ok or not secs:
            continue
        covered = sum(s[4] for s in secs) * 3
        if covered == idx_total:
            sections = secs
            break
        if best is None or covered > sum(s[4] for s in best):
            best = secs
    if not sections:
        sections = best or []

    return {
        "bbox_min": struct.unpack_from("<3f", d, start),
        "bbox_max": struct.unpack_from("<3f", d, start + 12),
        "sphere": struct.unpack_from("<4f", d, start + 24),
        "verts": verts,
        "uvs": uvs,
        "indices": render_idx,
        "sections": sections,
        "vertex_revision": 0,
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
    if mesh["uvs"]:
        # separate UV stream (the 24-B pos+normal vertex format)
        uv_flat = []
        for u, v in mesh["uvs"][0]:
            uv_flat.extend([u, 1.0 - v])
    elif len(mesh["verts"][0]) == 8:
        # inline UVs (the 32/36-B interleaved vertex format)
        uv_flat = []
        for v in mesh["verts"]:
            uv_flat.extend([v[6], 1.0 - v[7]])
    else:
        uv_flat = [0.0, 0.0] * len(mesh["verts"])

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
    secs = mesh.get("sections") or [(0, 0, len(mesh["verts"]) - 1, 0,
                                     len(mesh["indices"]) // 3)]
    used = 0
    for (fi, fv, lv, fe, nf) in secs:
        sub = mesh["indices"][fi:fi + nf * 3]  # FirstIndex is in index units
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
            # hint: the verified vertex count from the existing staged glTF
            hint = 0
            staged_root = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), os.pardir, 'assets', 'maps',
                '20_18', 'meshes')
            staged_root = os.path.normpath(staged_root)
            for root, _dirs, files in os.walk(staged_root):
                if name + '.gltf' in files:
                    try:
                        sg = json.load(open(os.path.join(root, name + '.gltf')))
                        hint = sum(
                            sg['accessors'][pr['attributes']['POSITION']]['count']
                            for pr in sg['meshes'][0]['primitives'])
                    except (json.JSONDecodeError, KeyError, OSError):
                        pass
                    break
            mesh = parse_static_mesh(pkg.data, bulk,
                                     e.serial_size - obj.end, hint_verts=hint)
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
