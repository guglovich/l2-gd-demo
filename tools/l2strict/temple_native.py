#!/usr/bin/env python3
"""Native Shillien Temple builder (2026-11-16, the user's modern-port rule).

The whole temple interior (floors, walls, the stair ramps) is authored in
the client as CSG_Subtract brush volumes; the level BSP Model500 contains
NONE of it (model_full.py: zero surf geometry in the temple region) and no
static meshes cover it either. Rendering those subtract faces through the
legacy brush pipeline (the bsp2.py csg=2 switch) was tried and REVERTED:
that is the legacy-crutch port the modern-port rule forbids (emulating the
2000s CSG carve result through the brush renderer).

This builder is the approved path: it takes ONLY the client coordinates
(the subtract volumes' face polygons + their FPoly texture axes) and emits
a clean native Godot mesh — one primitive per texture, UVs = texels from
the authored texture axes, the same uv_is_texels convention the level BSP
uses — no CsgOper semantics, no carving, no brush-pipeline emulation.

Input : tmp/decrypted/MAPS/20_18.unr + assets/maps/20_18/bsp.json
        (the brush<->polys pairing with locations, csg opers)
Output: assets/maps/20_18/meshes_bsp/TempleNative.gltf/.bin
        assets/maps/20_18/temple_native.json (surfaces[] with tex pairs)

The region filter (X 25500..31500, Y 8800..17200) selects the temple
subtract volumes only: the two stair ramps (Polys71/59, the 26.1-degree
marches with the ai_004 step texture), the gallery slopes (Polys31/35/47/51,
45 degrees, in008/in023) and the temple floors/walls. The road strip (X
6300..17220) is untouched, so the golden baseline cannot regress.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_probe import Package  # noqa: E402
from levelbsp import resolve_tex  # noqa: E402
from bsp2 import parse_polys  # noqa: E402

SCALE = 0.01
# the temple subtract volumes (see the module docstring)
REGION = (25500, 31500, 8800, 17200)
FACE_SKIP_FLAGS = 0x1 | 0x80 | 0x4000000  # invisible, fake backdrop, portal


def main() -> None:
    map_path, asset_dir = sys.argv[1], sys.argv[2]
    out_dir = os.path.join(asset_dir, "meshes_bsp")
    pkg = Package(map_path)
    shaders = json.load(open(os.path.join(asset_dir, "shader_diffuse.json")))
    bsp = json.load(open(os.path.join(asset_dir, "bsp.json")))

    polys_exports = {}
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) == "Polys":
            polys_exports[pkg.name(pkg.exports[i][3])] = i

    groups = {}          # tex_key -> [(verts, uvs)]  (texture groups)
    stats = {"brushes": 0, "faces": 0, "skipped_flags": 0, "skipped_tex": 0}
    for br in bsp["brushes"]:
        if br.get("csg") != 2:
            continue
        loc = br["location"]
        if not (REGION[0] <= loc[0] <= REGION[1]
                and REGION[2] <= loc[1] <= REGION[3]):
            continue
        pi = polys_exports.get(br["polys"])
        if pi is None:
            continue
        e = pkg.exports[pi]
        d = pkg.data[e[6]:e[6] + e[5]]
        stats["brushes"] += 1
        for pr in parse_polys(d, e[5]):
            if pr["flags"] & FACE_SKIP_FLAGS:
                stats["skipped_flags"] += 1
                continue
            tex = resolve_tex(pkg, pr["poly_mat"], shaders)
            if not tex:
                stats["skipped_tex"] += 1
                continue
            base = [pr["base"][k] + loc[k] for k in range(3)]
            tu, tv = pr["tu"], pr["tv"]
            verts = []
            uvs = []
            for v in pr["verts"]:
                w = [v[k] + loc[k] for k in range(3)]
                verts.append(w)
                uvs.append((sum((w[k] - base[k]) * tu[k] for k in range(3)),
                            sum((w[k] - base[k]) * tv[k] for k in range(3))))
            groups.setdefault(tuple(tex), []).append((verts, uvs))
            stats["faces"] += 1

    # build the glTF: one primitive per texture group, Godot axes (x, z, y),
    # meters — the level BSP convention (uv_is_texels on the shader side)
    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    mesh_prims = []
    surfaces = []
    for key in sorted(groups.keys()):
        pos = []
        uvs = []
        idx = []
        vbase = 0
        for verts, uvs2 in groups[key]:
            for v in verts:
                pos.extend([v[0] * SCALE, v[2] * SCALE, v[1] * SCALE])
            for u, w in uvs2:
                uvs.extend([u, w])
            n = len(verts)
            for k in range(1, n - 1):
                idx.extend([vbase, vbase + k + 1, vbase + k])
            vbase += n
        if not idx:
            continue
        pb = struct.pack(f"<{len(pos)}f", *pos)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob),
                             "byteLength": len(pb)})
        blob.extend(pb)
        accessors.append({"bufferView": len(buffer_views) - 1,
                          "componentType": 5126, "count": len(pos) // 3,
                          "type": "VEC3",
                          "min": [min(pos[0::3]), min(pos[1::3]),
                                  min(pos[2::3])],
                          "max": [max(pos[0::3]), max(pos[1::3]),
                                  max(pos[2::3])]})
        ub = struct.pack(f"<{len(uvs)}f", *uvs)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob),
                             "byteLength": len(ub)})
        blob.extend(ub)
        accessors.append({"bufferView": len(buffer_views) - 1,
                          "componentType": 5126, "count": len(uvs) // 2,
                          "type": "VEC2"})
        ib = struct.pack(f"<{len(idx)}I", *idx)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob),
                             "byteLength": len(ib)})
        blob.extend(ib)
        accessors.append({"bufferView": len(buffer_views) - 1,
                          "componentType": 5125, "count": len(idx),
                          "type": "SCALAR"})
        while len(blob) % 4:
            blob.append(0)
        si = len(mesh_prims)
        materials.append({"name": f"m{si}",
                          "pbrMetallicRoughness":
                              {"baseColorFactor": [0.4, 0.4, 0.4, 1.0]},
                          "doubleSided": True})
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 3,
                                          "TEXCOORD_0": len(accessors) - 2},
                           "indices": len(accessors) - 1, "material": si,
                           "mode": 4})
        surfaces.append({"tex": list(key)})

    gltf = {
        "asset": {"version": "2.0", "generator": "l2godot temple_native"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "TempleNative"}],
        "meshes": [{"name": "TempleNative", "primitives": mesh_prims}],
        "materials": materials,
        "accessors": accessors, "bufferViews": buffer_views,
        "buffers": [{"uri": "TempleNative.bin", "byteLength": len(blob)}],
    }
    json.dump(gltf, open(os.path.join(out_dir, "TempleNative.gltf"), "w"))
    open(os.path.join(out_dir, "TempleNative.bin"), "wb").write(bytes(blob))
    json.dump({"schema": 1, "surfaces": surfaces},
              open(os.path.join(asset_dir, "temple_native.json"), "w"),
              indent=1)
    print(f"temple_native: brushes {stats['brushes']}, faces {stats['faces']} "
          f"(skipped flags {stats['skipped_flags']}, tex {stats['skipped_tex']}), "
          f"{len(mesh_prims)} surfaces, {len(blob)} bytes")
    for s in surfaces:
        print("   surface tex:", s["tex"])


if __name__ == "__main__":
    main()
