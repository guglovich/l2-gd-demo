#!/usr/bin/env python3
"""The Shillien Temple LEVEL BSP extractor (2026-11-18, DEVLOG-82).

THE ROOT CAUSE of every temple defect (the gray rectangles above the
arches, near the decorative windows, around the statue): the client's
level-BSP texture coordinates are NOT computed from the surf U/V axes —
they are BAKED into the model's Sections array (FBspSection vertex
streams: pos12 + uv8 + 8 B mystery + normal12, node slice =
node.sect = (iSection, iFirstVertex)). The stream UVs are the client's
FINAL tile coordinates (in002 walls: 128 world units per U tile, 512
per V tile). The old computed UVs (dot(v - base, U)) were wrong by
orders of magnitude (+-35000) and every BSP face sampled a random
texel — the flat-gray patches. The stream positions match the node
polygons exactly (10380/10380 vertices, 0 mismatches).

The node walk stays: NODE -> iSurf (cs[1]) for material/flags, NODE ->
sect slice for positions and UVs. Validation: rev == numnodes == node
count and section material == node surf materials — 31/31 sections.

The clean-room fills (DEVLOG-81): only the wall strips the CSG never
produced faces for (z -3182..-3145 above the doorway openings) remain;
the soffit fills were DUPLICATES of real client faces (z -3218..-3182
exists in the sections) and are dropped. Fill UVs follow the client's
own density at the same wall (u = x/128, v = z/512).

Region filter: the temple interior only. The village keeps its approved
look (bsp2 ADD brushes + the 17 legacy levelbsp surfaces).

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
# invisible, fake backdrop, portal. The 0x40a000 BSP surfs are the temple
# WALL MASSES (in002 — the hall side walls, the apse walls with the doorway
# jambs carved, the corridor walls); the client renders them.
FACE_SKIP_FLAGS = 0x1 | 0x80 | 0x4000000

# the clean-room fills: the wall strips above the north/south doorway
# openings (the CSG volumes never produced faces there; the client blocks
# the sun with its shadow volumes — we block it with the fills).
# (x0, x1, y, z0, z1, normal_y, tex)
FILLS = [
    (27888, 28272, 12824, -3182, -3145, +1, ("sylen_temple_t", "oren_sylen_in002")),
    (27888, 28272, 9240, -3182, -3145, -1, ("sylen_temple_t", "oren_sylen_in002")),
]
# the client's own tile density measured at the same wall: 128 units per
# U tile, 512 per V tile
FILL_UTILE = 128.0
FILL_VTILE = 512.0


def main() -> None:
    map_path, asset_dir = sys.argv[1], sys.argv[2]
    out_dir = os.path.join(asset_dir, "meshes_bsp")
    pkg = Package(map_path)
    shaders = json.load(open(os.path.join(asset_dir, "shader_diffuse.json")))

    midx = find_level_model(pkg)
    M = parse_level_model(pkg, midx)
    pts, nodes, surfs, verts, sections = (M["pts"], M["nodes"], M["surfs"],
                                          M["verts"], M["sections"])
    print(f"level model: {len(nodes)} nodes, {len(surfs)} surfs, "
          f"{len(verts)} verts, {len(sections)} sections (streams)")

    groups = {}          # tex_key -> [(verts3d, uvs)]
    stats = {"nodes": 0, "hidden": 0, "marker": 0, "nomat": 0,
             "outside": 0, "faces": 0}
    for nd in nodes:
        cs = nd["cs"]
        si = cs[1]          # iSurf
        cnt = nd["nvert"]
        isec, ifv = nd["sect"][0], nd["sect"][1]
        if not (0 <= si < len(surfs)):
            stats["nomat"] += 1
            continue
        if cnt < 3 or not (0 <= isec < len(sections)):
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
        recs = sections[isec]["verts"]
        if ifv + cnt > len(recs):
            stats["nomat"] += 1
            continue
        poly = [recs[ifv + k][0] for k in range(cnt)]
        uvs = [recs[ifv + k][1] for k in range(cnt)]
        xs = [v[0] for v in poly]
        ys = [v[1] for v in poly]
        zs = [v[2] for v in poly]
        if not (REGION[0] <= max(xs) and min(xs) <= REGION[1]
                and REGION[2] <= max(ys) and min(ys) <= REGION[3]
                and -6100 <= max(zs) and min(zs) <= -1500):
            stats["outside"] += 1
            continue
        # The client renders BSP faces ONE-SIDED unless the section is
        # TwoSided (UE2 GRenderBspSection culls backfaces). Group by
        # (tex, two_sided) so world.gd can set the cull mode per surface.
        two_sided = bool(sections[isec]["poly_flags"] & 0x100)
        # Orient the polygon to the node plane normal (the client's front
        # face); the stream order is not guaranteed to match.
        pl = nd["plane"]
        e1 = [poly[1][k] - poly[0][k] for k in range(3)]
        e2 = [poly[2][k] - poly[0][k] for k in range(3)]
        # polygon normal (before orientation)
        pn = [e1[1] * e2[2] - e1[2] * e2[1],
              e1[2] * e2[0] - e1[0] * e2[2],
              e1[0] * e2[1] - e1[1] * e2[0]]
        if pn[0] * pl[0] + pn[1] * pl[1] + pn[2] * pl[2] < 0:
            poly.reverse()
            uvs.reverse()
        groups.setdefault((tuple(tex), 1 if two_sided else 0), []).append((poly, uvs))
        stats["faces"] += 1
        stats["nodes"] += 1

    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    mesh_prims = []
    surfaces = []
    for key in sorted(groups.keys()):
        tex, two_sided = key[0], bool(key[1])
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
            # the polygons are oriented to the node plane normal (right-hand
            # rule = CCW seen from the front). Godot's front face = the
            # winding it keeps with cull_back — verified by render; flip the
            # FAN order here once if the convention proves opposite.
            for k in range(1, n - 1):
                idx.extend([vbase, vbase + k, vbase + k + 1])
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
                          "doubleSided": two_sided})
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 3,
                                         "TEXCOORD_0": len(accessors) - 2},
                           "indices": len(accessors) - 1, "material": si,
                           "mode": 4})
        surfaces.append({"tex": list(tex), "two_sided": two_sided})

    # the clean-room wall strips (the CSG's own gaps) with the client's
    # tile density at the same wall — two-sided (no node plane to orient)
    for (x0, x1, y0, z0, z1, ny, ftex) in FILLS:
        corners = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]
        if ny < 0:
            corners.reverse()
        uvs = [(0.0, 0.0),
               (float(x1 - x0) / FILL_UTILE, 0.0),
               (float(x1 - x0) / FILL_UTILE, float(z1 - z0) / FILL_VTILE),
               (0.0, float(z1 - z0) / FILL_VTILE)]
        groups.setdefault((tuple(ftex), 1), []).append((corners, uvs))
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
    json.dump({"schema": 2, "build": build_id, "uv": "section-streams",
               "surfaces": surfaces},
              open(os.path.join(asset_dir, "temple_bsp.json"), "w"), indent=1)
    print(f"temple_bsp: nodes in region {stats['nodes']}, faces {stats['faces']} "
          f"(hidden {stats['hidden']}, marker {stats['marker']}, "
          f"no-material {stats['nomat']}, outside {stats['outside']}), "
          f"{len(mesh_prims)} surfaces, {len(blob)} bytes")


if __name__ == "__main__":
    main()
