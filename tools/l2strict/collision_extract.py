#!/usr/bin/env python3
"""Extract the authentic L2 collision subset per static mesh.

The 29-B units ([01][XX][YY][81 81] + 2 corners) are the collision-tree
leaf bboxes. The engine collides only the triangles covered by them.
This tool scans a package's StaticMesh exports, reads the staged glTF,
keeps the triangles whose centroid falls inside any unit bbox and writes
<mesh>.collision.json next to it: {"tris": [x,y,z ...], "units": N}.
Coordinates are written in the staged glTF frame (meters) so world.gd can
build a trimesh directly.
"""
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from l2strict.package import Package
from l2strict.properties import read_object


def scan_units(d, start, end):
    out = []
    p = start
    while p + 29 <= end:
        if d[p] == 0x01 and d[p + 3] == 0x81 and d[p + 4] == 0x81:
            vs = struct.unpack_from('<6f', d, p + 5)
            p += 29
            if all(abs(t) < 5000 for t in vs):
                out.append(vs)
        else:
            p += 1
    return out


def extract(pkg: Package, name: str, gltf_path: str) -> bool:
    e = None
    for i in range(pkg.export_count):
        if pkg.class_name_of_export(i) == "StaticMesh" and \
                pkg.name(pkg.exports[i].object_name) == name:
            e = pkg.exports[i]
            break
    if e is None:
        return False
    obj = read_object(pkg.data[e.serial_offset:e.serial_offset + e.serial_size],
                      pkg, context=name,
                      has_stack=bool(e.object_flags & 0x02000000))
    bulk = e.serial_offset + obj.end
    end = e.serial_offset + e.serial_size
    units = scan_units(pkg.data, bulk, end)
    if not units:
        return False

    g = json.load(open(gltf_path))
    base = os.path.dirname(gltf_path)
    buf = open(os.path.join(base, g["buffers"][0]["uri"]), "rb").read()
    boxes = []  # (min, max) in the native (X, Y, Z) unit frame, cm
    for vs in units:
        a = np.array(vs[:3], dtype=np.float64)
        b = np.array(vs[3:], dtype=np.float64)
        boxes.append((np.minimum(a, b), np.maximum(a, b)))

    keep = []
    for pr in g["meshes"][0]["primitives"]:
        pa = g["accessors"][pr["attributes"]["POSITION"]]
        bv = g["bufferViews"][pa["bufferView"]]
        # staged glTF vertex = (fileX, fileZ, fileY) * 0.01 where the file
        # order is (X, height, Y-width); the unit frame is (X, Y, Z=height),
        # so the glTF->unit remap is (x, z, y).
        pos = np.frombuffer(buf, "<f4", pa["count"] * 3,
                            bv.get("byteOffset", 0)).reshape(-1, 3).astype(np.float64)
        cent = pos.reshape(-1, 3)
        cunit = cent[:, [0, 2, 1]] * 100.0  # back to cm in the unit frame
        if "indices" not in pr:
            continue
        ia = g["accessors"][pr["indices"]]
        bi = g["bufferViews"][ia["bufferView"]]
        idx = np.frombuffer(buf, "<H", ia["count"], bi.get("byteOffset", 0))
        tris = idx.reshape(-1, 3)
        tc = cunit[tris].mean(axis=1)  # per-triangle centroid (unit frame)
        tol = 3.0
        mask = np.zeros(len(tris), dtype=bool)
        for lo, hi in boxes:
            inside = ((tc >= lo - tol) & (tc <= hi + tol)).all(axis=1)
            mask |= inside
        for t, m in zip(tris, mask):
            if m:
                for vi in t:
                    keep.extend(pos[vi].tolist())
    if not keep:
        return False
    out = {"units": len(units), "tris": len(keep) // 9, "verts": keep}
    with open(gltf_path.rsplit("/", 1)[0] + f"/{name}.collision.json", "w") as f:
        json.dump(out, f)
    return True


def main() -> None:
    pkg_path, staged_dir = sys.argv[1], sys.argv[2]
    pkg = Package.from_file(pkg_path)
    names = set()
    for i in range(pkg.export_count):
        if pkg.class_name_of_export(i) == "StaticMesh":
            names.add(pkg.name(pkg.exports[i].object_name))
    done = missed = nounits = 0
    for f in sorted(os.listdir(staged_dir)):
        if not f.endswith(".gltf") or f[:-5] not in names:
            continue
        name = f[:-5]
        gltf_path = os.path.join(staged_dir, f)
        if extract(pkg, name, gltf_path):
            done += 1
        else:
            missed += 1
            print(f"  no collision: {name}")
    print(f"collision.json written for {done} meshes, {missed} without")


if __name__ == "__main__":
    main()
