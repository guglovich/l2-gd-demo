#!/usr/bin/env python3
"""Render the LEVEL BSP from the client's baked SECTION vertex streams.

The licensee-25+ maps (18_19, 21_18, 20_17) store their Model POINTS in a
format the licensee-23 float parse reads as garbage (the bbox-corner
pattern ±327680/±262144/±16384), while every COMPACT array (nodes, surfs,
verts) parses fine and the SECTIONS validate structurally
(rev == numnodes == the per-section node count).

The sections ARE the client's render data: per material, a vertex stream
of 40-byte records (pos12 + uv8 + 8 mystery + normal12) — the positions
are the real geometry and the UVs are the client's FINAL tile
coordinates (DEVLOG-82). The section's nodes (FBspNode iSection) map
onto the stream as ordered runs: sum(node.nvert) == section.nvert
(validated 18/18 on 18_19), and each run is one polygon (a fan).

Output (the same contract as levelbsp.py, consumed by world.gd
_build_bsp unchanged):
  <out_dir>/LevelBSP.gltf/.bin  — one primitive per material, meters,
                                  Godot axes, UVs = the client tile coords
  <asset_dir>/levelbsp.json     — {"surfaces": [{"tex": [pkg, obj]|null,
                                                "texel_uvs": false}]}
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_probe import Package  # noqa: E402

SCALE = 0.01
MAX_SPAN = 7000.0
# the L2 world height limits (the deepest dungeon ~ -100 m, the sky ~ +120 m);
# the zone-box corner polys leak here at exactly +-163.84 m — beyond any
# real L2 geometry (DEVLOG-116)
MAX_ABS_Z = 13000.0


def read_compact(d, p):
    b0 = d[p]
    p += 1
    mag = b0 & 0x3F
    if b0 & 0x40:
        sh = 6
        while True:
            b = d[p]
            p += 1
            mag |= (b & 0x7F) << sh
            sh += 7
            if not b & 0x80:
                break
    return (-mag if b0 & 0x80 else mag), p


def resolve_tex(pkg, ref, shaders):
    if not isinstance(ref, int) or ref == 0:
        return None
    if ref > 0:
        j = ref - 1
        if j >= pkg.export_count:
            return None
        cls = pkg.class_of_export(j)
        nm = pkg.name(pkg.exports[j][3])
        if cls == "Texture":
            return [None, nm]
        if cls == "Shader":
            diff = shaders.get(f"::{nm}") or shaders.get(nm)
            if diff:
                return [None, diff]
        return None
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
    if cls == "Texture":
        return [pkg_file.lower() if pkg_file else pkg_file, obj]
    if cls == "Shader":
        diff = shaders.get(f"{pkg_file}::{obj}") if pkg_file else None
        if diff:
            return [pkg_file.lower() if pkg_file else pkg_file, diff]
    return None


def main():
    map_path, asset_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    pkg = Package(map_path)
    shaders_path = os.path.join(asset_dir, "shader_diffuse.json")
    shaders = json.load(open(shaders_path)) if os.path.isfile(shaders_path) else {}

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "levelbsp", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "levelbsp.py"))
    lb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lb)

    midx = lb.find_level_model(pkg)
    if midx is None:
        print("no level Model found")
        return
    M = lb.parse_level_model(pkg, midx)
    nodes, secs = M["nodes"], M["sections"]
    print(f"level model export {midx}: {len(nodes)} nodes, {len(secs)} sections")

    # the node runs per section, in the node order
    runs = {}
    for nd in nodes:
        runs.setdefault(nd["sect"][0], []).append(nd["nvert"])

    groups = {}  # tex_key -> list of polygons [(verts3d, uvs)]
    stats = {"drawn": 0, "portal": 0, "nomat": 0, "span": 0, "runmismatch": 0}
    for si, sec in enumerate(secs):
        tex = resolve_tex(pkg, sec["mat"], shaders)
        nm = sec["mat"] if isinstance(sec["mat"], int) else 0
        imp = -nm - 1
        cls_name = ""
        if nm < 0 and 0 <= imp < len(pkg.imports):
            cls_name = pkg.name(pkg.imports[imp][1])
        if cls_name in ("ZonePortal", "AntiPortal") or \
                (tex and tex[1] in ("ZonePortal", "AntiPortal")):
            stats["portal"] += 1
            continue
        if not tex:
            stats["nomat"] += 1
            continue
        r = runs.get(si, [])
        if sum(r) != sec["nvert"]:
            stats["runmismatch"] += 1
            continue
        verts = sec["verts"]
        pos = 0
        for nvert in r:
            if nvert < 3 or pos + nvert > len(verts):
                pos += nvert
                continue
            poly = [verts[pos + k][0] for k in range(nvert)]
            uv = [verts[pos + k][1] for k in range(nvert)]
            xs = [v[0] for v in poly]
            ys = [v[1] for v in poly]
            zs = [v[2] for v in poly]
            if (max(xs) - min(xs)) > MAX_SPAN or (max(ys) - min(ys)) > MAX_SPAN \
                    or max(abs(z) for z in zs) > MAX_ABS_Z:
                stats["span"] += 1
            else:
                key = tuple(tex)
                groups.setdefault(key, []).append((poly, uv))
                stats["drawn"] += 1
            pos += nvert
    print("sections: drawn %d, portal %d, no-material %d, huge-span %d, "
          "run-mismatch %d" % (stats["drawn"], stats["portal"], stats["nomat"],
                               stats["span"], stats["runmismatch"]))

    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    mesh_prims = []
    surfaces = []
    for key in sorted(groups.keys()):
        tex = list(key)
        si = len(mesh_prims)
        pos = []
        uvs = []
        idx = []
        vbase = 0
        for poly, uv in groups[key]:
            for v in poly:
                pos.extend([v[0] * SCALE, v[2] * SCALE, v[1] * SCALE])
            for u, w in uv:
                uvs.extend([u, w])
            n = len(poly)
            for k in range(1, n - 1):
                idx.extend([vbase, vbase + k + 1, vbase + k])
            vbase += n
        if not idx:
            continue
        pb = struct.pack(f"<{len(pos)}f", *pos)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(pb)})
        blob.extend(pb)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                          "count": len(pos) // 3, "type": "VEC3",
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
        materials.append({"name": f"m{si}", "pbrMetallicRoughness":
                          {"baseColorFactor": [0.4, 0.4, 0.4, 1.0]},
                          "doubleSided": True})
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 3,
                                          "TEXCOORD_0": len(accessors) - 2},
                           "indices": len(accessors) - 1, "material": si, "mode": 4})
        # the section UVs = the client's FINAL tile coordinates — the runtime
        # must NOT rescale them by the texture size (texel_uvs=false)
        surfaces.append({"tex": tex, "texel_uvs": False})

    gltf = {
        "asset": {"version": "2.0", "generator": "l2godot level_sections"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "LevelBSP"}],
        "meshes": [{"name": "LevelBSP", "primitives": mesh_prims}],
        "materials": materials,
        "accessors": accessors, "bufferViews": buffer_views,
        "buffers": [{"uri": "LevelBSP.bin", "byteLength": len(blob)}],
    }
    json.dump(gltf, open(os.path.join(out_dir, "LevelBSP.gltf"), "w"))
    open(os.path.join(out_dir, "LevelBSP.bin"), "wb").write(bytes(blob))
    json.dump({"schema": 1, "surfaces": surfaces},
              open(os.path.join(asset_dir, "levelbsp.json"), "w"), indent=1)
    print(f"LevelBSP: {len(mesh_prims)} surfaces, {len(blob)} bytes")


if __name__ == "__main__":
    main()
