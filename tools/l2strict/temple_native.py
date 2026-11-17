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
# DEVLOG-76 face rule (the client's brush rendering, reverse-engineered from
# the flag split + the user's reports): a Brush poly face renders IFF its
# flags are 0x0. The 0x40a000 set (NoOcclude|Translucent|Modulate) marks the
# ZONE-BOUNDARY faces of the volume boxes (Polys17 the hall box — all 6 faces,
# Polys55/67 the corridor wrappers — all 6, Polys23/28 — 5 of 6 faces: the
# marker stone in002 everywhere). Rendering them produced the gray in002
# squares and the alien interior walls. ZonePortal faces (0x4000109) and the
# invisible/fake-backdrop families are skipped as before.
FACE_SKIP_FLAGS = 0x1 | 0x80 | 0x4000000 | 0x40A000

# The air-air caps are computed automatically (v6.1): a SUBTRACT face whose
# plane is the touching plane of two carved volumes (or of a carved volume
# and an ADD solid) is an interior CSG face — the client's load-time carve
# removes it. Manual overrides for the faces bordering OUTSIDE air (the
# world's air is not a box): the vestibule west cap (Polys39 poly 0, the
# entrance facade) and the corridor outside ends (Polys71/59 poly 3), plus
# the vestibule bottom (poly 5, the solid-solid z-fight with Polys43).
MANUAL_CAP_EXCLUDE = {
    "Polys39": {0, 5},
    "Polys71": {3},
    "Polys59": {3},
}

# The hall wall bands (Polys23 poly 1 at Y 10528, Polys28 poly 3 at Y 11536 —
# the only 0x0 faces of those slabs, texture oren_sylen_001_1) span the
# corridor doorways (x 27880..28280 — the sidedoor01/02 tunnel boxes). The
# client's doorways are open: the wall quads are split into west strip +
# east strip + lintel (above z -3411) around each opening.
DOORWAY = (27880.0, 28280.0, -3411.0)   # x0, x1, lintel bottom z
WALL_FACES = {"Polys23": 1, "Polys28": 3}


def _emit_face(pr, origin, groups, stats, cut_rects=None):
    """Emit one poly (optionally split around door cuts) into groups."""
    tex = pr["_tex"]
    base = [pr["base"][k] + origin[k] for k in range(3)]
    tu, tv = pr["tu"], pr["tv"]

    def uv_of(w):
        return (sum((w[k] - base[k]) * tu[k] for k in range(3)),
                sum((w[k] - base[k]) * tv[k] for k in range(3)))

    verts = [[v[k] + origin[k] for k in range(3)] for v in pr["verts"]]
    quads = [(verts, uv_of)]
    if cut_rects:
        # plane axes: the face is axis-aligned; find the two varying axes
        mins = [min(v[k] for v in verts) for k in range(3)]
        maxs = [max(v[k] for v in verts) for k in range(3)]
        var = [k for k in range(3) if maxs[k] - mins[k] > 1.0]
        if len(var) == 2:
            ax, bx = var          # a = the wide axis (x), b = the other
            a0, a1 = mins[ax], maxs[ax]
            b0, b1 = mins[bx], maxs[bx]
            dx0, dx1, lintel = cut_rects
            # normal of the original poly (winding reference)
            A, B, C = verts[0], verts[1], verts[2]
            n = [(B[1]-A[1])*(C[2]-A[2]) - (B[2]-A[2])*(C[1]-A[1]),
                 (B[2]-A[2])*(C[0]-A[0]) - (B[0]-A[0])*(C[2]-A[2]),
                 (B[0]-A[0])*(C[1]-A[1]) - (B[1]-A[1])*(C[0]-A[0])]
            def quad(r0, r1, s0, s1):
                corners = []
                for (a, b) in ((r0, s0), (r1, s0), (r1, s1), (r0, s1)):
                    w = [0.0, 0.0, 0.0]
                    w[ax], w[bx] = a, b
                    for k in range(3):
                        if k not in var:
                            w[k] = mins[k]
                    corners.append(w)
                n2 = [(corners[1][1]-corners[0][1])*(corners[2][2]-corners[0][2]) - (corners[2][1]-corners[0][1])*(corners[1][2]-corners[0][2]),
                      (corners[1][2]-corners[0][2])*(corners[2][0]-corners[0][0]) - (corners[2][2]-corners[0][2])*(corners[1][0]-corners[0][0]),
                      (corners[1][0]-corners[0][0])*(corners[2][1]-corners[0][1]) - (corners[2][0]-corners[0][0])*(corners[1][1]-corners[0][1])]
                if n[0]*n2[0] + n[1]*n2[1] + n[2]*n2[2] < 0:
                    corners.reverse()
                return corners
            quads = [
                (quad(a0, dx0, b0, b1), uv_of),
                (quad(dx1, a1, b0, b1), uv_of),
                (quad(dx0, dx1, lintel, b1), uv_of),
            ]
    for corners, uvf in quads:
        groups.setdefault(tuple(tex), []).append(
            (corners, [uvf(w) for w in corners]))
        stats["faces"] += 1


def main() -> None:
    map_path, asset_dir = sys.argv[1], sys.argv[2]
    out_dir = os.path.join(asset_dir, "meshes_bsp")
    pkg = Package(map_path)
    shaders = json.load(open(os.path.join(asset_dir, "shader_diffuse.json")))

    polys_parse = {}
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) == "Polys":
            e = pkg.exports[i]
            polys_parse[i] = parse_polys(pkg.data[e[6]:e[6] + e[5]], e[5])

    groups = {}          # tex_key -> [(verts, uvs)]
    stats = {"add": 0, "sub": 0, "faces": 0, "skip_flags": 0, "skip_tex": 0,
             "skip_caps": 0, "cut": 0}

    # --- pass 1: the carved-volume boxes (for the air-air touch test) -----
    # SUBTRACT brushes carve air; Polys17 (the hall box, all faces 0x40a000)
    # carves the hall air too; ADD brushes are the solids the voids sit
    # on/in. A subtract face is an interior CSG face (never rendered) when
    # its plane is exactly the touching plane with another such box.
    boxes = []           # (pname, min[3], max[3], csg, poly_index)
    brush_face_data = []  # (pname, csg, origin, prs, j)
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
        prs = polys_parse[j]
        brush_face_data.append((pname, csg, origin, prs))
        if csg == 2 or pname == "Polys17":
            mins = [min(v[k] for pr in prs for v in pr["verts"]) + origin[k]
                    for k in range(3)]
            maxs = [max(v[k] for pr in prs for v in pr["verts"]) + origin[k]
                    for k in range(3)]
            boxes.append((pname, mins, maxs, csg))
        elif csg == 1:
            # ADD solids participate as the solid side of void-on-solid joints
            mins = [min(v[k] for pr in prs for v in pr["verts"]) + origin[k]
                    for k in range(3)]
            maxs = [max(v[k] for pr in prs for v in pr["verts"]) + origin[k]
                    for k in range(3)]
            boxes.append((pname, mins, maxs, 1))

    def touching(my_pname, mins, maxs):
        """planes {axis: value} where another box touches this one with an
        overlapping footprint (the shared faces are interior CSG faces)."""
        planes = {}
        for pname, bmin, bmax, _csg in boxes:
            if pname == my_pname:
                continue
            for k in range(3):
                # this box's min face touched by the other's max face
                if abs(bmax[k] - mins[k]) < 1.0 and all(
                        bmin[m] < maxs[m] - 1.0 and bmax[m] > mins[m] + 1.0
                        for m in range(3) if m != k):
                    planes.setdefault(k, set()).add(mins[k])
                if abs(bmin[k] - maxs[k]) < 1.0 and all(
                        bmin[m] < maxs[m] - 1.0 and bmax[m] > mins[m] + 1.0
                        for m in range(3) if m != k):
                    planes.setdefault(k, set()).add(maxs[k])
        return planes

    # --- pass 2: emit the faces ------------------------------------------
    for pname, csg, origin, prs in brush_face_data:
        stats["add" if csg == 1 else "sub"] += 1
        manual = MANUAL_CAP_EXCLUDE.get(pname, set()) if csg == 2 else set()
        planes = None
        if csg == 2:
            mins = [min(v[k] for pr in prs for v in pr["verts"]) + origin[k]
                    for k in range(3)]
            maxs = [max(v[k] for pr in prs for v in pr["verts"]) + origin[k]
                    for k in range(3)]
            planes = touching(pname, mins, maxs)
        cut = DOORWAY if (csg == 1 and pname in WALL_FACES) else None
        for pr in prs:
            if pr["flags"] & FACE_SKIP_FLAGS:
                stats["skip_flags"] += 1
                continue
            if pr["i"] in manual:
                stats["skip_caps"] += 1
                continue
            if planes is not None:
                # the face's plane: the axis with zero extent
                lo = [min(v[k] for v in pr["verts"]) + origin[k] for k in range(3)]
                hi = [max(v[k] for v in pr["verts"]) + origin[k] for k in range(3)]
                axis = next((k for k in range(3) if hi[k] - lo[k] < 1.0), None)
                if axis is not None and lo[axis] in planes.get(axis, ()):
                    stats["skip_caps"] += 1
                    continue
            tex = resolve_tex(pkg, pr["poly_mat"], shaders)
            if not tex or tex[1] in ("AntiPortal", "ZonePortal"):
                stats["skip_tex"] += 1
                continue
            pr["_tex"] = tex
            rects = DOORWAY if (cut and pr["i"] == WALL_FACES[pname]) else None
            if rects:
                stats["cut"] += 1
            _emit_face(pr, origin, groups, stats, rects)

    def build_gltf(groups, mesh_name):
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
            "nodes": [{"mesh": 0, "name": mesh_name}],
            "meshes": [{"name": mesh_name, "primitives": mesh_prims}],
            "materials": materials,
            "accessors": accessors, "bufferViews": buffer_views,
            "buffers": [{"uri": f"{mesh_name}.bin", "byteLength": len(blob)}],
        }
        return gltf, blob, surfaces, mesh_prims

    gltf, blob, surfaces, mesh_prims = build_gltf(groups, "TempleNative")
    json.dump(gltf, open(os.path.join(out_dir, "TempleNative.gltf"), "w"))
    open(os.path.join(out_dir, "TempleNative.bin"), "wb").write(bytes(blob))
    json.dump({"schema": 1, "surfaces": surfaces},
              open(os.path.join(asset_dir, "temple_native.json"), "w"),
              indent=1)
    print(f"temple_native v6 (flag rule): ADD {stats['add']}, "
          f"SUB {stats['sub']}, faces {stats['faces']} "
          f"(caps {stats['skip_caps']}, flags {stats['skip_flags']}, "
          f"tex {stats['skip_tex']}, door cuts {stats['cut']}), "
          f"{len(mesh_prims)} surfaces, {len(blob)} bytes")


if __name__ == "__main__":
    main()
