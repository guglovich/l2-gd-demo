#!/usr/bin/env python3
"""Extract map data (actors, terrain info, dependencies) from decrypted L2 .unr.

Usage: python3 l2_extract.py MAP.unr OUT.json
"""
import json
import sys

from l2_probe import Package
from l2_props import read_object


def import_package_chain(pkg, imp_idx):
    """Return package file name for an import (walk outer chain)."""
    cp, cn, pk, nm = pkg.imports[imp_idx]
    parts = [pkg.name(nm)]
    cur = pk
    while cur != 0:
        if cur > 0:
            break  # outer export (e.g. group) — stop
        imp = -cur - 1
        if not (0 <= imp < len(pkg.imports)):
            break
        parts.append(pkg.name(pkg.imports[imp][3]))
        cur = pkg.imports[imp][2]
    # chain: ObjectName, then outer packages...
    return parts[-1] if parts else pkg.name(nm)


def resolve_ref(pkg, ref):
    """ref: compact int from ObjectProperty. Returns (kind, package, object, class)."""
    if ref == 0:
        return None
    if ref > 0:
        e = pkg.exports[ref - 1]
        return ("export", None, pkg.name(e[3]), pkg.class_of_export(ref - 1))
    imp = -ref - 1
    cp, cn, pk, nm = pkg.imports[imp]
    # package file = outer chain of the import (usually the usx/utx package import)
    pkg_file = None
    cur = pk
    while cur != 0:
        if cur > 0:
            e = pkg.exports[cur - 1]
            pkg_file = pkg.name(e[3])
            break
        imp2 = -cur - 1
        if not (0 <= imp2 < len(pkg.imports)):
            break
        pkg_file = pkg.name(pkg.imports[imp2][3])
        cur = pkg.imports[imp2][2]
    return ("import", pkg_file, pkg.name(nm), pkg.name(cn))


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    path, out = sys.argv[1], sys.argv[2]
    p = Package(path)
    pr = read_object

    actors = []
    terrain = None
    packages = {}  # file name -> set of object names
    classes_count = {}

    WANTED = ("StaticMeshActor", "MovableStaticMeshActor",
              "L2MovableStaticMeshActor", "PlayerStart", "TerrainInfo")

    for i in range(p.export_count):
        cls, sup, pk, nm, fl, size, off = p.exports[i]
        cls_name = p.class_of_export(i)
        classes_count[cls_name] = classes_count.get(cls_name, 0) + 1
        if size == 0 or cls_name not in WANTED:
            continue
        data = p.data[off:off + size]
        try:
            state, props, end = read_object(data, p, has_stack=bool(fl & 0x02000000))
        except Exception as e:
            actors.append({"class": cls_name, "name": p.name(nm), "error": str(e)})
            continue

        if cls_name in ("StaticMeshActor", "MovableStaticMeshActor",
                        "L2MovableStaticMeshActor", "PlayerStart"):
            mesh_ref = props.get("StaticMesh")
            mesh = None
            if isinstance(mesh_ref, int) and mesh_ref < 0:
                r = resolve_ref(p, mesh_ref)
                if r:
                    mesh = {"package": r[1], "object": r[2]}
                    if r[1]:
                        packages.setdefault(r[1], set()).add(r[2])
            actors.append({
                "class": cls_name,
                "name": p.name(nm),
                "location": props.get("Location", (0.0, 0.0, 0.0)),
                "rotation": props.get("Rotation", (0, 0, 0)),
                "draw_scale": props.get("DrawScale", 1.0),
                "draw_scale3d": props.get("DrawScale3D", (1.0, 1.0, 1.0)),
                "pre_pivot": props.get("PrePivot", (0.0, 0.0, 0.0)),
                "mesh": mesh,
            })
        elif cls_name == "TerrainInfo":
            layers = []
            raw_layers = props.get("Layers")
            if isinstance(raw_layers, list):
                for li, l in enumerate(raw_layers):
                    if not isinstance(l, dict):
                        continue
                    tex = l.get("Texture")
                    amap = l.get("AlphaMap")
                    tex_info = resolve_ref(p, tex) if isinstance(tex, int) else None
                    amap_info = resolve_ref(p, amap) if isinstance(amap, int) else None
                    if tex_info and tex_info[1]:
                        packages.setdefault(tex_info[1], set()).add(tex_info[2])
                    if amap_info and amap_info[1]:
                        packages.setdefault(amap_info[1], set()).add(amap_info[2])
                    layers.append({
                        "texture": tex_info[2] if tex_info else None,
                        "texture_pkg": tex_info[1] if tex_info else None,
                        "alpha_map": amap_info[2] if amap_info else None,
                        "alpha_pkg": amap_info[1] if amap_info else None,
                        "u_scale": l.get("UScale", 1.0),
                        "v_scale": l.get("VScale", 1.0),
                        "scale": l.get("Scale", (0.0, 0.0, 0.0)),
                    })
            tm = props.get("TerrainMap")
            tm_info = resolve_ref(p, tm) if isinstance(tm, int) else None
            if tm_info and tm_info[1]:
                packages.setdefault(tm_info[1], set()).add(tm_info[2])
            terrain = {
                "name": p.name(nm),
                "terrain_map": tm_info[2] if tm_info else None,
                "terrain_map_pkg": tm_info[1] if tm_info else None,
                "terrain_scale": props.get("TerrainScale", (128.0, 128.0, 76.0)),
                "layers": layers,
            }

    result = {
        "map": path,
        "terrain": terrain,
        "actors": actors,
        "packages": {k: sorted(v) for k, v in packages.items()},
        "classes_count": classes_count,
    }
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    n_actors = sum(1 for a in actors if "error" not in a)
    print(f"extracted {n_actors} actors, packages: {len(result['packages'])}")
    for pkg_name, objs in result["packages"].items():
        print(f"  {pkg_name}: {len(objs)} objects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
