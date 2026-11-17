#!/usr/bin/env python3
"""The Shillien Temple LEVEL BSP extractor (2026-11-17, DEVLOG-77).

THE ROOT CAUSE of every temple defect (the alien walls, the gray squares,
the statue voids, the missing floor): the temple interior IS the level BSP.
model_full.py's temple probe was broken — it used surf idx[4] (iBrushPoly)
as a NODE index — and reported "zero temple geometry". In truth 336 BSP
nodes (walls with the carved panel recesses, floors, ceilings, bands) sit
in the temple region of Model500, and the client renders exactly that:
the level BSP + the decoration static meshes. The Brush actors are the
CSG SOURCES (their own Models are empty, the runtime renders nothing
from them — engine.dll has no runtime CSG at all).

levelbsp.py's extractor has the same broken mapping (it iterates SURFS and
reads idx[4] as a node index — 774 surfs shrink to 17 surfaces), so the
temple BSP never reached the render. This tool extracts the temple part of
the level BSP the way the client walks it: NODE → iSurf (cs[1]) → material /
UV axes / flags; NODE → iVertPool (cs[0]) + NumVertices → the polygon.

Region filter: the temple interior only. The village keeps its approved
look (bsp2 ADD brushes + the 17 legacy levelbsp surfaces) — the full-BSP
village swap is a separate task needing the baseline re-approval.

Output: assets/maps/20_18/meshes_bsp/TempleBsp.gltf/.bin
        assets/maps/20_18/temple_bsp.json (surfaces[] with tex pairs)
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_probe import Package  # noqa: E402
from levelbsp import parse_level_model, find_level_model, resolve_tex  # noqa: E402

SCALE = 0.01
REGION = (25400, 31500, 8800, 17200)
# invisible, fake backdrop, portal. NOTE (DEVLOG-78 rev2): the 0x40a000
# BSP surfs are the temple WALL MASSES (in002 — ~130 faces: the hall side
# walls, the apse walls with the doorway jambs carved, the corridor
# walls); the client renders them — skipping them left the "gray
# rectangle" holes. Only Invisible/FakeBackdrop/Portal skip.
FACE_SKIP_FLAGS = 0x1 | 0x80 | 0x4000000


def main() -> None:
    map_path, asset_dir = sys.argv[1], sys.argv[2]
    out_dir = os.path.join(asset_dir, "meshes_bsp")
    pkg = Package(map_path)
    shaders = json.load(open(os.path.join(asset_dir, "shader_diffuse.json")))

    midx = find_level_model(pkg)
    M = parse_level_model(pkg, midx)
    vec, pts, nodes, surfs, verts = (M["vec"], M["pts"], M["nodes"],
                                     M["surfs"], M["verts"])
    print(f"level model: {len(nodes)} nodes, {len(surfs)} surfs, "
          f"{len(verts)} verts, {len(pts)} points")

    groups = {}          # tex_key -> [(verts3d, uvs)]
    stats = {"nodes": 0, "hidden": 0, "marker": 0, "nomat": 0,
             "outside": 0, "faces": 0}
    for nd in nodes:
        cs = nd["cs"]
        si = cs[1]          # iSurf
        pool, cnt = cs[0], nd["nvert"]
        if not (0 <= si < len(surfs)):
            stats["nomat"] += 1
            continue
        if cnt < 3 or pool + cnt > len(verts):
            stats["nomat"] += 1
            continue
        s = surfs[si]
        if s["flags"] & FACE_SKIP_FLAGS:
            stats["hidden"] += 1
            continue
        tex = resolve_tex(pkg, s["mat"], shaders)
        if not tex or tex[1] in ("AntiPortal", "ZonePortal"):
            stats["marker"] += 1
            continue
        poly = []
        ok = True
        for k in range(cnt):
            vi = verts[pool + k][0]
            if not (0 <= vi < len(pts)):
                ok = False
                break
            poly.append(pts[vi])
        if not ok:
            stats["nomat"] += 1
            continue
        xs = [v[0] for v in poly]
        ys = [v[1] for v in poly]
        zs = [v[2] for v in poly]
        if not (REGION[0] <= max(xs) and min(xs) <= REGION[1]
                and REGION[2] <= max(ys) and min(ys) <= REGION[3]
                and -6100 <= max(zs) and min(zs) <= -1500):
            stats["outside"] += 1
            continue
        base = pts[s["idx"][0]]
        U = vec[s["idx"][2]]
        V = vec[s["idx"][3]]
        uvs = [(sum((v[k] - base[k]) * U[k] for k in range(3)),
                sum((v[k] - base[k]) * V[k] for k in range(3))) for v in poly]
        groups.setdefault(tuple(tex), []).append((poly, uvs))
        stats["faces"] += 1
        stats["nodes"] += 1

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
        for verts3d, uvs2 in groups[key]:
            for v in verts3d:
                pos.extend([v[0] * SCALE, v[2] * SCALE, v[1] * SCALE])
            for u, w in uvs2:
                uvs.extend([u, w])
            n = len(verts3d)
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

    # DEVLOG-81: the CLEAN-ROOM fills — the wall bands the CSG never
    # produced faces for: the strips between the corridor lintels
    # (z -3218) and the skin facade bottom (-3145) above the north/south
    # doorway openings (x 27888..28272), facing the platforms. Without
    # them the sun pours through the facade holes and lights the in008
    # gallery bands inside (the "gray rectangles"). Texture = in002, the
    # same stone the BSP walls use. Facing: +y (north fill) / -y (south).
    fills = [
        # (x0, x1, y, z0, z1, normal_y, tex)
        (27888, 28272, 12824, -3182, -3145, +1, ("sylen_temple_t", "oren_sylen_in002")),
        (27888, 28272, 9240, -3182, -3145, -1, ("sylen_temple_t", "oren_sylen_in002")),
        # the doorway soffits (the opening ceilings): z -3218..-3182 facing down
        (27888, 28272, 12824, -3218, -3182, -1, ("sylen_temple_t", "oren_sylen_in002")),
        (27888, 28272, 9240, -3218, -3182, -1, ("sylen_temple_t", "oren_sylen_in002")),
    ]
    for (x0, x1, y0, z0, z1, ny, ftex) in fills:
        # the quad in the plane y = y0 (or z = z0 for the soffits: use y-plane too)
        corners = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]
        if ny < 0:
            corners.reverse()
        uvs = [(0.0, 0.0), (float(x1-x0)/64.0, 0.0),
               (float(x1-x0)/64.0, float(z1-z0)/64.0), (0.0, float(z1-z0)/64.0)]
        groups.setdefault(tuple(ftex), []).append((corners, uvs))
        stats["faces"] += 1

    gltf = {
        "asset": {"version": "2.0", "generator": "l2godot temple_bsp"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "TempleBsp"}],
        "meshes": [{"name": "TempleBsp", "primitives": mesh_prims}],
        "materials": materials,
        "accessors": accessors, "bufferViews": buffer_views,
        "buffers": [{"uri": "TempleBsp.bin", "byteLength": len(blob)}],
    }
    json.dump(gltf, open(os.path.join(out_dir, "TempleBsp.gltf"), "w"))
    open(os.path.join(out_dir, "TempleBsp.bin"), "wb").write(bytes(blob))
    import time
    build_id = "temple-bsp " + time.strftime("%Y-%m-%d %H:%M")
    json.dump({"schema": 1, "build": build_id, "surfaces": surfaces},
              open(os.path.join(asset_dir, "temple_bsp.json"), "w"), indent=1)
    print(f"temple_bsp: nodes in region {stats['nodes']}, faces {stats['faces']} "
          f"(hidden {stats['hidden']}, marker {stats['marker']}, "
          f"no-material {stats['nomat']}, outside {stats['outside']}), "
          f"{len(mesh_prims)} surfaces, {len(blob)} bytes")


if __name__ == "__main__":
    main()
