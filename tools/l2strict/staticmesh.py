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
            if f4 != 0 or fi < prev_fi or nf == 0:
                ok = False
                break
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
    """Parse one StaticMesh export binary bulk (props already consumed).

    Layout (verified from engine.dll + Oren_DEV_S):
      BoundingBox 24B -> [gap] -> sections (14B entries) -> [gap] ->
      VertexStream (compact count, count*24B pos+normal, i32 revision) ->
      ColorStream -> AlphaStream -> UVStreams -> IndexStream1/2 -> ...
    """
    r = Reader(data, start)
    bbox_min = struct.unpack_from("<3f", data, r.p)
    bbox_max = struct.unpack_from("<3f", data, r.p + 12)
    r.p += 24
    sphere = struct.unpack_from("<4f", data, r.p)
    r.p += 16

    # --- vertex stream: [compact count][count * stride]; the stride is
    # 24 B (pos+normal) or 32 B (pos+normal+uv interleaved) -- both exist
    # in Oren_DEV_S (Bridge=24B, Pir01/obj04=32B).
    def _ok_rec(data, p, stride):
        x, y, z, nx, ny, nz = struct.unpack_from("<6f", data, p)
        if not all(abs(v) < 1.2e5 for v in (x, y, z)):
            return False
        if not all(abs(v) <= 1.001 for v in (nx, ny, nz)):
            return False
        if abs(nx * nx + ny * ny + nz * nz - 1.0) >= 0.02:
            return False
        if stride == 32:
            u, v = struct.unpack_from("<2f", data, p + 24)
            if abs(u) > 16 or abs(v) > 16:
                return False
        return True

    def _scan_runs(data, start, size, stride):
        # byte-wise scan with a cheap exponent filter: a position float in
        # +-64..+-131072 has biased exponent 130..142, top byte (sign|E>>1)
        # = 0x41..0x48 (positive) or 0xC1..0xC8 (negative)
        best_start, best_len, p = 0, 0, start
        end = start + size - stride
        while p < end:
            hi = data[p + 3] & 0x7F
            if 0x41 <= hi <= 0x48 and _ok_rec(data, p, stride):
                run = 0
                q = p
                while q < end and _ok_rec(data, q, stride):
                    run += 1
                    q += stride
                if run > best_len:
                    best_start, best_len = p, run
                p = max(q, p + 1)
            else:
                p += 1
        return best_start, best_len

    uvs = []
    if hint_verts >= 8:
        # exact anchor: find the byte pattern of the compact encoding of the
        # known vertex count, then validate the records after it
        def compact_bytes(n: int) -> bytes:
            b0 = (n & 0x3F) | 0x40
            rest = n >> 6
            out = [b0]
            while rest:
                nxt = rest >> 7
                out.append((rest & 0x7F) | (0x80 if nxt else 0))
                rest = nxt
            return bytes(out)
        pat = compact_bytes(hint_verts)
        found_at = None
        q = start
        while True:
            q = data.find(pat, q, start + size)
            if q < 0:
                break
            for stride in (24, 32):
                if q + 2 + min(hint_verts, 64) * stride <= start + size:
                    good = sum(
                        1 for i in range(min(hint_verts, 64))
                        if _ok_rec(data, q + 2 + i * stride, stride)
                    )
                    if good == min(hint_verts, 64):
                        found_at = q + 2
                        break
            if found_at is not None:
                break
            q += 1
        if found_at is None:
            raise ValueError("vertex stream anchor not found (hinted)")
        vstart, vcount, stride = found_at, hint_verts, stride
    else:
        vs24, n24 = _scan_runs(data, start, size, 24)
        vs32, n32 = _scan_runs(data, start, size, 32)
        if n32 > n24:
            vstart, vcount, stride = vs32, n32, 32
        else:
            vstart, vcount, stride = vs24, n24, 24
        if vcount < 8:
            raise ValueError(f"vertex stream anchor not found (24:{n24} 32:{n32})")
    verts = []
    for i in range(vcount):
        p = vstart + i * stride
        x, y, z, nx, ny, nz = struct.unpack_from("<6f", data, p)
        uv = struct.unpack_from("<2f", data, p + 24) if stride == 32 else (0.0, 0.0)
        verts.append((x, y, z, nx, ny, nz, uv[0], uv[1]))
    r = Reader(data, vstart + vcount * stride)
    vert_revision = r.i32()

    # --- color / alpha streams
    for _ in range(2):
        n = r.compact()
        if 0 < n < 200000 and r.p + n * 4 + 4 <= start + size:
            r.p += n * 4
        r.i32()

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
        indices.append(struct.unpack_from(f"<{n}H", data, r.p))
        r.p += n * 2
        r.i32()
    render_idx = None
    for idx in indices:
        if idx and max(idx) < len(verts):
            render_idx = idx
            break
    if render_idx is None:
        raise ValueError("no render index stream referencing the vertex pool")

    sections = _find_sections(data, start + 24, vstart,
                              len(render_idx) // 3)

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
    if mesh["uvs"]:
        uv_flat = []
        for u, v in mesh["uvs"][0]:
            uv_flat.extend([u, 1.0 - v])
    else:
        uv_flat = []
        for v in mesh["verts"]:
            uv_flat.extend([v[6], 1.0 - v[7]])

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
