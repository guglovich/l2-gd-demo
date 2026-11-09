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

    # --- the authentic collision triangle records (fnd_9/10) ---
    # TArray<FStaticMeshCollisionTriangle>::Serialize = {compact count} +
    # count back-to-back records of 16 dwords + 4 compacts (~68 B). The
    # plane = d12..d15, the vertices = d0..d8 (9 floats). The records are
    # NOT 4-aligned to the bulk (the compact tails break the grid), so the
    # scan is byte-wise for the plane pattern (|n| ~ 1, sane D).
    d = pkg.data
    n_seg = end - bulk
    raw = d[bulk:end]
    plane_hits = []
    i = 0
    while i < n_seg - 68:
        nx, ny, nz, D = struct.unpack_from('<4f', raw, i)
        if abs(nx * nx + ny * ny + nz * nz - 1.0) < 1e-4 and -1e5 < D < 1e5:
            # candidate plane: require the same pattern at +68 (the stride)
            nx2, ny2, nz2, D2 = struct.unpack_from('<4f', raw, i + 68)
            if abs(nx2 * nx2 + ny2 * ny2 + nz2 * nz2 - 1.0) < 1e-4 and -1e5 < D2 < 1e5:
                plane_hits.append(i)
                i += 68
                continue
        i += 1
    # --- the authentic collision records (fnd_9/10 + the plane layout) ---
    # The record = 4 planes (the face + 3 edges, 16 B each = 64 B) + 4
    # FCompactIndex (iVertex[3] + MaterialIndex) = 68 B, back-to-back, NOT
    # 4-aligned to the bulk. The triangle verts = the intersections of the
    # face plane with the adjacent edge plane pairs.
    raw = pkg.data[bulk:end]
    n_seg = len(raw)
    plane_hits = []
    i = 0
    while i < n_seg - 68:
        nx, ny, nz, D = struct.unpack_from('<4f', raw, i)
        if abs(nx * nx + ny * ny + nz * nz - 1.0) < 1e-4 and -1e5 < D < 1e5:
            nx2, ny2, nz2, D2 = struct.unpack_from('<4f', raw, i + 68)
            if abs(nx2 * nx2 + ny2 * ny2 + nz2 * nz2 - 1.0) < 1e-4 and -1e5 < D2 < 1e5:
                plane_hits.append(i)
                i += 68
                continue
        i += 1
    keep = []
    recs = 0
    for ph in plane_hits:
        planes = []
        ok = True
        for pi in range(4):
            n = np.array(struct.unpack_from('<3f', raw, ph + pi * 16), dtype=np.float64)
            D = struct.unpack_from('<f', raw, ph + pi * 16 + 12)[0]
            if abs(np.linalg.norm(n) - 1.0) > 1e-3:
                ok = False
                break
            planes.append((n, float(D)))
        if not ok:
            continue
        face = planes[0]
        verts3 = []
        good = True
        for ei in range(3):
            e1 = planes[1 + ei]
            e2 = planes[1 + (ei + 1) % 3]
            A = np.array([face[0], e1[0], e2[0]])
            b = np.array([face[1], e1[1], e2[1]])
            if abs(np.linalg.det(A)) < 1e-9:
                good = False
                break
            v = np.linalg.solve(A, b)
            verts3.append(v)
        if not good or len(verts3) != 3:
            continue
        if not all(np.all(np.abs(v) < 1e5) for v in verts3):
            continue
        for v in verts3:
            x, y, z = v  # the file native (X, Y-width, Z-up)
            keep.extend([x * 0.01, z * 0.01, y * 0.01])
        recs += 1
    print(f"  {name}: {recs} collision records")
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
