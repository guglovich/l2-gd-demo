#!/usr/bin/env python3
"""Export BSP brush geometry (Polys objects) of a decrypted L2 map.

Outputs (into ASSET_DIR):
  meshes_bsp/BSP_<Polys>.gltf/.bin  — local space, meters, Godot axes
  bsp.json — {brushes, materials, cover_cells}
    cover_cells: [row, col] cells of the 128-unit terrain grid whose area is
    covered by a brush polygon in world (x,y) — used by world.gd to keep
    terrain holes open ONLY above actual cave geometry.
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_probe import Package  # noqa: E402
from l2_props import read_object  # noqa: E402

SCALE = 0.01
CELL = 128.0


def parse_polys(d, size):
    r = 1  # props: None terminator
    num = struct.unpack_from("<i", d, r)[0]
    r += 4
    r += 4  # max

    def cidx(rr):
        b = d[rr]
        if b & 0x40:
            v = b & 0x3F
            sh = 6
            rr += 1
            while True:
                b = d[rr]
                rr += 1
                v |= (b & 0x7F) << sh
                sh += 7
                if not b & 0x80:
                    break
            return (-(v + 1) if b & 0x80 else v), rr
        return (-(b & 0x3F) - 1) if b & 0x80 else (b & 0x3F), rr + 1

    polys = []
    for _ in range(num):
        vc, r = cidx(r)
        base = struct.unpack_from("<3f", d, r)
        r += 12
        normal = struct.unpack_from("<3f", d, r)
        r += 12
        tu = struct.unpack_from("<3f", d, r)
        r += 12
        tv = struct.unpack_from("<3f", d, r)
        r += 12
        verts = []
        for _ in range(vc):
            verts.append(struct.unpack_from("<3f", d, r))
            r += 12
        flags = struct.unpack_from("<I", d, r)[0]
        r += 4
        actor, r = cidx(r)
        mat, r = cidx(r)
        item, r = cidx(r)
        link, r = cidx(r)
        bpoly, r = cidx(r)
        r += 4   # LightMapScale
        r += 4   # trailing i32
        if vc < 3:
            continue
        if flags & (0x04000000 | 0x00000001 | 0x00000080):
            continue  # portal / invisible / fake backdrop
        polys.append({
            "verts": verts, "normal": normal, "tu": tu, "tv": tv,
            "base": base, "flags": flags, "mat": mat,
        })
    return polys


def resolve_mat(pkg, ref, shaders):
    if not isinstance(ref, int) or ref == 0:
        return None
    if ref > 0:
        return [None, pkg.name(pkg.exports[ref - 1][3])]
    imp = -ref - 1
    if not (0 <= imp < len(pkg.imports)):
        return None
    cp, cn, pk, nm = pkg.imports[imp]
    cls = pkg.name(cn)
    obj = pkg.name(nm)
    pkg_file = None
    cur = pk
    while cur != 0:
        if cur > 0:
            pkg_file = pkg.name(pkg.exports[cur - 1][3])
            break
        imp2 = -cur - 1
        if not (0 <= imp2 < len(pkg.imports)):
            break
        o_cp, o_cn, o_pk, o_nm = pkg.imports[imp2]
        pkg_file = pkg.name(o_nm)
        if pkg.name(o_cn) == "Package":
            break
        cur = o_pk
    if cls not in ("Texture", "Shader"):
        return None
    if cls == "Shader":
        diff = shaders.get(f"{pkg_file}::{obj}")
        if diff:
            return diff
    return [pkg_file.lower() if pkg_file else pkg_file, obj]


def write_gltf(path, name, prims):
    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    mesh_prims = []
    for pi, prim in enumerate(prims):
        pts = prim["verts"]
        base = prim["base"]
        udir = tuple(prim["tu"][k] - base[k] for k in range(3))
        vdir = tuple(prim["tv"][k] - base[k] for k in range(3))
        uu = sum(c * c for c in udir)
        vv = sum(c * c for c in vdir)
        if uu < 1e-9 or vv < 1e-9:
            continue
        pos = []
        uvs = []
        for v in pts:
            pos.extend([v[0] * SCALE, v[2] * SCALE, v[1] * SCALE])
            u = sum((v[k] - base[k]) * udir[k] for k in range(3)) / uu
            w = sum((v[k] - base[k]) * vdir[k] for k in range(3)) / vv
            uvs.extend([u, w])
        idx = []
        for k in range(1, len(pts) - 1):
            idx.extend([0, k + 1, k])
        if len(idx) < 3:
            continue
        pb = struct.pack(f"<{len(pos)}f", *pos)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(pb)})
        blob.extend(pb)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                          "count": len(pts), "type": "VEC3",
                          "min": [min(pos[0::3]), min(pos[1::3]), min(pos[2::3])],
                          "max": [max(pos[0::3]), max(pos[1::3]), max(pos[2::3])]})
        ub = struct.pack(f"<{len(uvs)}f", *uvs)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(ub)})
        blob.extend(ub)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                          "count": len(uvs) // 2, "type": "VEC2"})
        ib = struct.pack(f"<{len(idx)}I", *idx)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(ib)})
        blob.extend(ib)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5125,
                          "count": len(idx), "type": "SCALAR"})
        while len(blob) % 4:
            blob.append(0)
        materials.append({"name": f"m{pi}", "pbrMetallicRoughness":
                          {"baseColorFactor": [0.4, 0.4, 0.4, 1.0]},
                          "doubleSided": True})
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 3,
                                          "TEXCOORD_0": len(accessors) - 2},
                           "indices": len(accessors) - 1, "material": pi, "mode": 4})
    if not mesh_prims:
        return False
    gltf = {
        "asset": {"version": "2.0", "generator": "l2godot bsp2"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": mesh_prims}],
        "materials": materials,
        "accessors": accessors, "bufferViews": buffer_views,
        "buffers": [{"uri": name + ".bin", "byteLength": len(blob)}],
    }
    json.dump(gltf, open(path + ".gltf", "w"))
    open(path + ".bin", "wb").write(bytes(blob))
    return True


def model_polys_ref(pkg, midx, loc, pivot, polys_parse):
    """The Brush->Model->Polys link. The L2 UModel::Serialize does NOT carry
    the stock-UE2 `Ar << Polys` at the head; the reference is a compact
    object index (export+1) inside the Model's binary blob (found by RE
    2026-11-12: Model954 blob holds compact 2260 = Polys370+1 at offset 55).
    Blobs can contain several compact values that decode into Polys exports
    (bbox floats coincide); the true one is picked by placing the geometry
    with origin = Location - PrePivot and requiring the brush Location to
    fall inside the resulting world bbox (+/-150)."""
    cls, sup, pk, nm, fl, size, off = pkg.exports[midx]
    d = pkg.data[off:off + size]
    cands = []
    p = 0
    while p < len(d):
        b = d[p]
        if b & 0x40:
            v = b & 0x3F
            sh = 6
            q = p
            ok = True
            while True:
                q += 1
                if q >= len(d):
                    ok = False
                    break
                b2 = d[q]
                v |= (b2 & 0x7F) << sh
                sh += 7
                if not b2 & 0x80:
                    break
            if ok:
                cands.append((p, v))
                p = q + 1
            else:
                p += 1
        else:
            cands.append((p, b & 0x3F if not b & 0x80 else -(b & 0x3F) - 1))
            p += 1
    refs = []
    for p, v in cands:
        j = v - 1
        if 0 <= j < pkg.export_count and pkg.class_of_export(j) == "Polys":
            refs.append((p, j))
    if not refs:
        return None
    if len(refs) == 1:
        return refs[0][1]
    origin = [loc[k] - pivot[k] for k in range(3)]
    for p, j in reversed(refs):
        P = polys_parse.get(j)
        if not P:
            continue
        vs = [v for pr in P for v in pr["verts"]]
        wmn = [min(v[k] for v in vs) + origin[k] for k in range(3)]
        wmx = [max(v[k] for v in vs) + origin[k] for k in range(3)]
        if all(wmn[k] - 150 <= loc[k] <= wmx[k] + 150 for k in range(3)):
            return j
    return refs[-1][1]


def main():
    map_path, asset_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    pkg = Package(map_path)
    shaders = json.load(open(os.path.join(asset_dir, "shader_diffuse.json")))

    # 1) parse every Polys object (local-space polygons)
    polys_objs = {}
    polys_parse = {}
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) != "Polys":
            continue
        cls, sup, pk, nm, fl, size, off = pkg.exports[i]
        name = pkg.name(nm)
        try:
            parsed = parse_polys(pkg.data[off:off + size], size)
            polys_objs[name] = parsed
            polys_parse[i] = parsed
        except Exception as e:
            print(f"polys {name}: {e}")

    # 2) brushes: Location (- PrePivot) + Polys via the compact ref inside
    # the Model blob (the name pairing ModelN/PolysN only holds for ~166 of
    # 249 brush-like actors; the street-floor brushes are NOT name-paired)
    brushes = []
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) != "Brush":
            continue
        cls, sup, pk, nm, fl, size, off = pkg.exports[i]
        d = pkg.data[off:off + size]
        try:
            state, props, end = read_object(d, pkg, bool(fl & 0x02000000))
        except Exception:
            continue
        bref = props.get("Brush")
        loc = props.get("Location", (0, 0, 0))
        pivot = props.get("PrePivot", (0, 0, 0))
        if not isinstance(bref, int) or bref <= 0:
            continue
        j = model_polys_ref(pkg, bref - 1, loc, pivot, polys_parse)
        if j is None:
            continue
        pname = pkg.name(pkg.exports[j][3])
        if pname not in polys_objs:
            continue
        origin = [loc[k] - pivot[k] for k in range(3)]
        flags = [pr["flags"] for pr in polys_objs[pname]]
        brushes.append({"polys": pname, "location": origin, "poly_flags": flags})

    # 3) export glTF per Polys + collect surface material refs
    os.makedirs(out_dir, exist_ok=True)
    mat_refs = {}
    exported = []
    for pname, prims in sorted(polys_objs.items()):
        refs = [resolve_mat(pkg, pr["mat"], shaders) for pr in prims]
        path = os.path.join(out_dir, f"BSP_{pname}")
        if not write_gltf(path, f"BSP_{pname}", prims):
            continue
        exported.append(pname)
        mat_refs[f"BSP:{pname}"] = refs

    # 4) coverage raster: world-space triangles -> 128u cells, tracking the
    # HIGHEST brush-plane height (meters) per cell within a sane world range.
    # Cells with valid cover stay open (cave below); cells whose only cover
    # is junk (Z out of range) get closed with interpolated terrain.
    cover_z = {}
    for b in brushes:
        prims = polys_objs.get(b["polys"])
        if not prims:
            continue
        loc = b["location"]
        for pr in prims:
            pts3 = [(loc[0] + v[0], loc[1] + v[1], loc[2] + v[2]) for v in pr["verts"]]
            if len(pts3) < 3:
                continue
            xs = [p[0] for p in pts3]
            ys = [p[1] for p in pts3]
            zs = [p[2] for p in pts3]
            if max(zs) < -12000.0 or min(zs) > 12000.0:
                continue  # junk coordinates
            c_lo = max(0, int(min(xs) // CELL))
            c_hi = min(255, int(max(xs) // CELL))
            r_lo = max(0, int(min(ys) // CELL))
            r_hi = min(255, int(max(ys) // CELL))
            if c_lo > c_hi or r_lo > r_hi:
                continue
            z0, x0, y0 = pts3[0]
            e1 = (pts3[1][0] - pts3[0][0], pts3[1][1] - pts3[0][1], pts3[1][2] - pts3[0][2])
            e2 = (pts3[2][0] - pts3[0][0], pts3[2][1] - pts3[0][1], pts3[2][2] - pts3[0][2])
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]
            norm = abs(nx) + abs(ny) + abs(nz)
            if norm < 1e-9 or abs(nz) / norm < 0.05:
                continue  # near-vertical wall: no walkable ground
            inv_nz = 1.0 / nz
            for cc in range(c_lo, c_hi + 1):
                for rr in range(r_lo, r_hi + 1):
                    px = (cc + 0.5) * CELL
                    py = (rr + 0.5) * CELL
                    d1 = (px - pts3[1][0]) * (pts3[0][1] - pts3[1][1]) - (pts3[0][0] - pts3[1][0]) * (py - pts3[1][1])
                    d2 = (px - pts3[2][0]) * (pts3[1][1] - pts3[2][1]) - (pts3[1][0] - pts3[2][0]) * (py - pts3[2][1])
                    d3 = (px - pts3[0][0]) * (pts3[2][1] - pts3[0][1]) - (pts3[2][0] - pts3[0][0]) * (py - pts3[0][1])
                    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                    if not (neg and pos):
                        continue
                    z_game = z0 - (nx * (px - x0) + ny * (py - y0)) * inv_nz
                    if z_game < -12000.0 or z_game > 8000.0:
                        continue  # plane explodes here (near-vertical edge)
                    z_val = z_game * SCALE
                    prev = cover_z.get((rr, cc))
                    if prev is None or z_val > prev:
                        cover_z[(rr, cc)] = z_val

    json.dump({
        "schema": 1,
        "brushes": brushes,
        "materials": mat_refs,
        "cover_z": [[r, c, round(z, 2)] for (r, c), z in sorted(cover_z.items())],
    }, open(os.path.join(asset_dir, "bsp.json"), "w"), indent=1)
    print(f"polys objects: {len(polys_objs)}, exported glTF: {len(exported)}, "
          f"brushes: {len(brushes)}, cover cells: {len(cover_z)}")


if __name__ == "__main__":
    main()
