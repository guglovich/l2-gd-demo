#!/usr/bin/env python3
"""Native Shillien Temple builder (2026-11-16, the user's modern-port rule).

The whole temple interior (floors, walls, the stair ramps) is authored in
the client as brush volumes; the level BSP Model500 contains NONE of it
(model_full.py: zero surf geometry in the temple region) and no static
meshes cover it either. Rendering the subtract faces through the legacy
brush pipeline (the bsp2.py csg=2 switch) was tried and REVERTED: that is
the legacy-crutch port the modern-port rule forbids.

This builder is the approved path: it takes ONLY the client coordinates
(the temple brush volumes' face polygons + their FPoly texture axes) and
emits a clean native Godot mesh — one primitive per texture, UVs = texels
from the authored texture axes, the same uv_is_texels convention the level
BSP uses — no CsgOper semantics, no carving, no brush-pipeline emulation.

Sources (all parsed DIRECTLY from the .unr, not from bsp.json — the
bsp2.json set is missing the temple floor brushes: the ADD volumes that
overlap subtract volumes are dropped there as legacy "housings"):
  ADD brushes      — the real temple geometry: the entrance floors
                     (Polys43/63), the main west passage stairs
                     (Polys83/79/87, the three ai_004 marches). Faces with
                     the zone-box flag set 0x40a000 (NoOcclude|Translucent —
                     the legacy INVISIBLE zone separators Polys17/23/28/55/67)
                     are NOT rendered, and ZonePortal faces are not either.
  SUBTRACT brushes — the interior volumes (the stair ramps Polys71/59, the
                     vestibule Polys39, the gallery slopes Polys31/35...).
                     Their AIR-AIR end caps are NOT rendered — in the live
                     client those faces sit between two carved (empty)
                     regions and never show; rendering them sealed the
                     temple entrances (the user's report: in the original
                     everything is open). The excluded caps, verified
                     against the entrance openings:
                       Polys71 poly 1,3 and Polys59 poly 1,3 (the corridor
                       end walls at Y 11784/12824 and 9240/10280)
                       Polys39 poly 0,2 (the vestibule west/east walls at
                       X 26328/26501 — the main entrance)

Region filter (X 25400..31500, Y 8800..17200) selects the temple volumes
only; the road strip (X 6300..17220) is untouched, so the golden baseline
cannot regress.

Output: assets/maps/20_18/meshes_bsp/TempleNative.gltf/.bin
        assets/maps/20_18/temple_native.json (surfaces[] with tex pairs)
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_probe import Package  # noqa: E402
from l2_props import read_object  # noqa: E402
from levelbsp import resolve_tex  # noqa: E402
from bsp2 import parse_polys, model_polys_ref  # noqa: E402

SCALE = 0.01
REGION = (25400, 31500, 8800, 17200)
FACE_SKIP_FLAGS = 0x1 | 0x80 | 0x4000000   # invisible, fake backdrop, portal
ZONE_BOX_FLAGS = 0x40A000                  # NoOcclude|Translucent|Modulate:
                                           # the legacy invisible zone boxes
# The subtract air-air end caps (the live client never renders them — see
# the module docstring): {polys name: set of raw poly indices}
SUBTRACT_CAP_EXCLUDE = {
    "Polys71": {1, 3},
    "Polys59": {1, 3},
    # Polys39 (the main-entrance vestibule) is carved air between two OPEN
    # regions: its west/east caps sealed the entrance, its top cap rendered
    # as a phantom floor at Z -3000 (the floor profile 26400,11032), its
    # bottom cap z-fights the Polys43 entrance slab at -3752. The whole
    # volume is air in the live client — none of its faces show.
    "Polys39": {0, 1, 2, 3, 4, 5},
}


def main() -> None:
    map_path, asset_dir = sys.argv[1], sys.argv[2]
    out_dir = os.path.join(asset_dir, "meshes_bsp")
    pkg = Package(map_path)
    shaders = json.load(open(os.path.join(asset_dir, "shader_diffuse.json")))

    # the ADD brushes already rendered by bsp2 (from bsp.json) — do not
    # duplicate their faces
    bsp = json.load(open(os.path.join(asset_dir, "bsp.json")))
    already = {br["polys"] for br in bsp["brushes"]}

    polys_parse = {}
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) == "Polys":
            e = pkg.exports[i]
            polys_parse[i] = parse_polys(pkg.data[e[6]:e[6] + e[5]], e[5])

    groups = {}          # tex_key -> [(verts, uvs)]
    stats = {"add": 0, "sub": 0, "faces": 0, "skip_flags": 0, "skip_tex": 0,
             "skip_zone": 0, "skip_caps": 0, "skip_dup": 0}
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) != "Brush":
            continue
        e = pkg.exports[i]
        d = pkg.data[e[6]:e[6] + e[5]]
        try:
            state, props, end = read_object(d, pkg, bool(e[4] & 0x02000000))
        except Exception:
            continue
        bref = props.get("Brush")
        if not isinstance(bref, int) or bref <= 0:
            continue
        csg = props.get("CsgOper", 1)
        csg = int(csg) if isinstance(csg, int) else 1
        loc = props.get("Location", (0, 0, 0))
        piv = props.get("PrePivot", (0, 0, 0))
        origin = [loc[k] - piv[k] for k in range(3)]
        if not (REGION[0] <= origin[0] <= REGION[1]
                and REGION[2] <= origin[1] <= REGION[3]):
            continue
        j = model_polys_ref(pkg, bref - 1, loc, piv, polys_parse)
        if j is None or j not in polys_parse:
            continue
        pname = pkg.name(pkg.exports[j][3])
        if csg == 1:
            if pname in already:
                stats["skip_dup"] += 1
                continue
            stats["add"] += 1
        else:
            stats["sub"] += 1
        caps = SUBTRACT_CAP_EXCLUDE.get(pname, set()) if csg == 2 else set()
        for pr in polys_parse[j]:
            if pr["flags"] & FACE_SKIP_FLAGS:
                stats["skip_flags"] += 1
                continue
            if csg == 1 and (pr["flags"] & ZONE_BOX_FLAGS) == ZONE_BOX_FLAGS:
                stats["skip_zone"] += 1
                continue
            if pr["i"] in caps:
                stats["skip_caps"] += 1
                continue
            tex = resolve_tex(pkg, pr["poly_mat"], shaders)
            if not tex or tex[1] in ("AntiPortal", "ZonePortal"):
                stats["skip_tex"] += 1
                continue
            base = [pr["base"][k] + origin[k] for k in range(3)]
            tu, tv = pr["tu"], pr["tv"]
            verts = []
            uvs = []
            for v in pr["verts"]:
                w = [v[k] + origin[k] for k in range(3)]
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
    print(f"temple_native: ADD {stats['add']}, SUB {stats['sub']} "
          f"(dup {stats['skip_dup']}), faces {stats['faces']} "
          f"(zone {stats['skip_zone']}, caps {stats['skip_caps']}, "
          f"flags {stats['skip_flags']}, tex {stats['skip_tex']}), "
          f"{len(mesh_prims)} surfaces, {len(blob)} bytes")


if __name__ == "__main__":
    main()
