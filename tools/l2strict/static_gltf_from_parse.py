#!/usr/bin/env python3
"""Regenerate a static-mesh glTF from the byte-validated L2 parse
(l2mesh_full), replacing the UModel export (DEVLOG-83, the hall floor).

Why: UModel's glTF export (1) FLIPS the texture v coordinate (glTF v' =
1 - v_ue) — wrong for the L2 client, whose D3D convention (v = 0 = the
image TOP) is the SAME as Godot's; invisible on v-symmetric stone, but
it explodes the 4-fold mirrored medallion (deco11/in021: the arcs fly
from the panel center to the outer edges — the "two arcs" defect), and
(2) rebuilt deco12 with lost tiling (u 0..1.5 / v 0.265..1 vs the
file's u 0..1 / v -0.958..1.985).

The parse is the same walker that validated 27/27 meshes EXACT to the
export end. UV convention: emit v VERBATIM (no flip). Sections: one
prim per non-empty section, prim k -> material section_index (identity,
fnd_22); materials array = props Materials count. Positions: UE cm ->
meters, axes (x, z, y). Winding: kept as stored (statics render
double-sided).

Usage:
  python3 -m tools.l2strict.static_gltf_from_parse <pkg.usx> <out_dir> <mesh> [mesh...]
out_dir = the StaticMesh dir holding the UModel exports (overwritten).
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2mesh_full as MF  # noqa: E402


def build(mesh_name: str, res: dict, mat_count: int):
    n = res["vertex_count"]
    verts = res["vertices"]          # (n, 6): UE x, y, z + ... per the parse
    uv = res["uv_streams"][0]["uv"]  # coord 0
    indices = res["indices"].tolist()
    pos = []
    for j in range(n):
        x, y, z = float(verts[j][0]), float(verts[j][1]), float(verts[j][2])
        pos.extend([x / 100.0, z / 100.0, y / 100.0])
    uvs = []
    for j in range(n):
        uvs.extend([float(uv[j][0]), float(uv[j][1])])

    blob = bytearray()
    views = []
    accs = []

    def add_view(data: bytes):
        views.append({"buffer": 0, "byteOffset": len(blob),
                      "byteLength": len(data)})
        blob.extend(data)
        while len(blob) % 4:
            blob.append(0)
        return len(views) - 1

    pb = struct.pack("<%df" % len(pos), *pos)
    pvi = add_view(pb)
    accs.append({"bufferView": pvi, "componentType": 5126,
                 "count": n, "type": "VEC3",
                 "min": [min(pos[0::3]), min(pos[1::3]), min(pos[2::3])],
                 "max": [max(pos[0::3]), max(pos[1::3]), max(pos[2::3])]})
    ub = struct.pack("<%df" % len(uvs), *uvs)
    uvi = add_view(ub)
    accs.append({"bufferView": uvi, "componentType": 5126,
                 "count": n, "type": "VEC2"})

    prims = []
    for si, sec in enumerate(res["sections"]):
        if sec["num_triangles"] <= 0 or sec["min_vertex"] == 65535:
            continue
        fi = sec["first_index"]
        cnt = sec["num_triangles"] * 3
        tris = indices[fi:fi + cnt]
        if sec["is_strip"]:
            # UE triangle strip: (i, i+1, i+2) with alternating winding
            exp = []
            for k in range(len(tris) - 2):
                a, b, c = tris[k], tris[k + 1], tris[k + 2]
                if k % 2:
                    exp.extend([a, c, b])
                else:
                    exp.extend([a, b, c])
            tris = exp
        ib = struct.pack("<%dH" % len(tris), *tris)
        ivi = add_view(ib)
        accs.append({"bufferView": ivi, "componentType": 5123,
                     "count": len(tris), "type": "SCALAR"})
        prims.append({"attributes": {"POSITION": 0, "TEXCOORD_0": 1},
                      "indices": len(accs) - 1,
                      "material": si, "mode": 4})

    materials = [{"name": "l2mat%d" % i,
                  "pbrMetallicRoughness":
                      {"baseColorFactor": [0.6, 0.6, 0.6, 1.0]},
                  "doubleSided": True}
                 for i in range(max(mat_count, 1))]
    gltf = {
        "asset": {"version": "2.0",
                  "generator": "l2godot static_gltf_from_parse"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": mesh_name}],
        "meshes": [{"name": mesh_name, "primitives": prims}],
        "materials": materials,
        "accessors": accs, "bufferViews": views,
        "buffers": [{"uri": mesh_name + ".bin", "byteLength": len(blob)}],
    }
    return gltf, bytes(blob)


def main() -> None:
    pkg_path, out_dir, *names = sys.argv[1:]
    pkg = MF.Package.from_file(pkg_path)
    wanted = set(names)
    done = []
    for i in range(pkg.export_count):
        if pkg.class_name_of_export(i) != "StaticMesh":
            continue
        e = pkg.exports[i]
        name = pkg.name(e.object_name)
        if wanted and name not in wanted:
            continue
        data = pkg.data[e.serial_offset:e.serial_offset + e.serial_size]
        obj = MF.read_object(data, pkg, context=name,
                             has_stack=bool(e.object_flags & 0x02000000))
        res = MF.parse_l2_static_mesh(data, obj.end, e.serial_size, name)
        mats = obj.props.values.get("Materials") or []
        if not isinstance(mats, list):
            mats = [mats]
        gltf, blob = build(name, res, len(mats))
        with open(os.path.join(out_dir, name + ".gltf"), "w") as f:
            json.dump(gltf, f)
        with open(os.path.join(out_dir, name + ".bin"), "wb") as f:
            f.write(blob)
        done.append((name, len(res["sections"]), res["vertex_count"]))
        print("%s: sections %d, verts %d -> %s" %
              (name, len(res["sections"]), res["vertex_count"], out_dir))
    if wanted:
        missing = wanted - {d[0] for d in done}
        if missing:
            raise SystemExit("meshes not found: %s" % sorted(missing))


if __name__ == "__main__":
    main()
