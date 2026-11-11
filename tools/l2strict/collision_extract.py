#!/usr/bin/env python3
"""Extract the authentic L2 collision subset per static mesh.

The on-disk collision array (engine.dll RE 2026-11-12, validated on
Oren_DEV_S — O_DE_Btm 690/690 and O_De_01 961/961 records pass plane·v=D):

    [compact N]                       N ≈ the mesh triangle count (can be
                                      off by 1: O_DE_WH 1167 vs 1166)
    N × record (VARIABLE stride):
        FPlane   planes[4]            4 × 16 B — the face + 3 edge planes
        compact  iVertex[3]           RAW VERTEX-STREAM indices (not wedges!)
        compact  MaterialIndex

Record stride is variable (64 B planes + 4-20 B of compacts) — the fixed
+68 stride of the first decoder caught only coincidental chains and
recovered ~5% of the triangles, silently dropping the WH porch, the plaza
floors and the stall decks.

The triangle vertices come from the mesh's raw 24-B vertex stream
(pos 12 B + normal 12 B) parsed straight out of the bulk — NOT from the
staged glTF, whose vertex order is renumbered by the per-prim staging
(the O_De_01 69+648 prim split). The winning stream is the one whose
positions satisfy every record's face plane (plane·v = D).

Output <mesh>.collision.json next to the glTF: {"units", "tris", "verts"}
in the staged glTF frame (meters, y-up) so world.gd builds a trimesh
directly. The kDOP leaf bboxes (the 29-B [01][XX][YY][81 81]+2 corners
records) gate which triangles the engine collides: only triangles whose
centroid falls inside some leaf bbox are kept.
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


def read_compact(d, p):
    b = d[p]
    if b & 0x40:
        v = b & 0x3F
        sh = 6
        while True:
            p += 1
            b = d[p]
            v |= (b & 0x7F) << sh
            sh += 7
            if not b & 0x80:
                break
        return v, p + 1
    return (b & 0x3F) if not (b & 0x80) else -(b & 0x3F) - 1, p + 1


def unit_plane(seg, off):
    if off + 16 > len(seg):
        return False
    nx, ny, nz, D = struct.unpack_from('<4f', seg, off)
    return abs(nx * nx + ny * ny + nz * nz - 1.0) < 1e-3 and -1e5 < D < 1e5


def walk_chain(seg, start, limit):
    """Walk variable-stride records from `start`; return (count, end_off)."""
    q = start
    n = 0
    while q + 64 <= limit:
        if not all(unit_plane(seg, q + 16 * k) for k in range(4)):
            break
        q += 64
        try:
            for _ in range(4):
                v, q = read_compact(seg, q)
                if v < 0 or v > 1000000:
                    return n, q
        except IndexError:
            break
        n += 1
    return n, q


def locate_array(seg):
    """Longest record chain whose preceding compact equals its length."""
    best = None
    o = 0
    while o + 64 <= len(seg):
        if all(unit_plane(seg, o + 16 * k) for k in range(4)):
            n, q = walk_chain(seg, o, len(seg))
            if n >= 8:
                for cs in range(o - 1, max(o - 6, -1), -1):
                    try:
                        v, p = read_compact(seg, cs)
                    except IndexError:
                        continue
                    if p == o and v == n:
                        if best is None or n > best[0]:
                            best = (n, o, q)
                        break
            o += 16
        else:
            o += 1
    return best  # (count, first_record_off, end_off)


def find_vertex_stream(seg, limit, records, max_idx):
    """Candidate 24-B vertex streams; return the one that best satisfies
    the records' face planes (the staged glTF vertex order is renumbered
    by per-prim staging, so the raw stream must be matched by validation)."""
    cands = []
    o = 0
    while o < limit:
        try:
            cnt, p = read_compact(seg, o)
        except IndexError:
            break
        if 4 <= cnt <= 60000 and cnt > max_idx and p + cnt * 24 <= limit:
            ok = 0
            try:
                for k in range(min(cnt, 12)):
                    x, y, z = struct.unpack_from('<3f', seg, p + k * 24)
                    nx, ny, nz = struct.unpack_from('<3f', seg, p + k * 24 + 12)
                    if (abs(x) < 1e6 and abs(y) < 1e6 and abs(z) < 1e6 and
                            abs(nx * nx + ny * ny + nz * nz - 1.0) < 0.01):
                        ok += 1
            except struct.error:
                ok = 0
            if ok == min(cnt, 12):
                cands.append((cnt, p))
        o += 1

    def validate(sp):
        ok = 0
        for planes, idx in records[:60]:
            nx, ny, nz, D = planes[0]
            good = True
            for k in idx[:3]:
                x, y, z = struct.unpack_from('<3f', seg, sp + k * 24)
                if abs(nx * x + ny * y + nz * z - D) > 2.0:
                    good = False
                    break
            if good:
                ok += 1
        return ok

    best = None
    for cnt, p in cands:
        v = validate(p)
        if best is None or v > best[0]:
            best = (v, cnt, p)
    return best


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
    seg = pkg.data[bulk:end]
    units = scan_units(seg, 0, len(seg))

    arr = locate_array(seg)
    if not arr:
        return False
    n, p, q = arr

    # decode every record once (planes + compacts)
    records = []
    pp = p
    mx = 0
    for _ in range(n):
        planes = [struct.unpack_from('<4f', seg, pp + 16 * k) for k in range(4)]
        pp += 64
        idx = []
        for _ in range(4):
            v, pp = read_compact(seg, pp)
            idx.append(v)
        mx = max(mx, max(idx[:3]))
        records.append((planes, idx))

    st = find_vertex_stream(seg, p, records, mx)
    if not st:
        return False
    _, cnt, sp = st

    boxes = []
    for vs in units:
        a = np.array(vs[:3], dtype=np.float64)
        b = np.array(vs[3:], dtype=np.float64)
        boxes.append((np.minimum(a, b), np.maximum(a, b)))

    verts = []
    kept = 0
    valid = 0
    for planes, idx in records:
        nx, ny, nz, D = planes[0]
        tri = []
        good = True
        cent = [0.0, 0.0, 0.0]
        for k in idx[:3]:
            x, y, z = struct.unpack_from('<3f', seg, sp + k * 24)
            if abs(nx * x + ny * y + nz * z - D) > 2.0:
                good = False
                break
            cent[0] += x / 3
            cent[1] += y / 3
            cent[2] += z / 3
            # staged glTF frame: (x, z-up→y, y-width→z) cm → m
            tri.extend([x * 0.01, z * 0.01, y * 0.01])
        if not good:
            continue
        valid += 1
        if boxes:
            c = np.array(cent)
            if not any(np.all(c >= lo) and np.all(c <= hi) for lo, hi in boxes):
                continue
        verts.extend(tri)
        kept += 1

    print(f"  {name}: {n} records, stream {cnt}v, {valid} plane-valid, "
          f"{kept} kept by {len(units)} kDOP units")
    if not kept:
        return False
    out = {"units": len(units), "tris": kept, "verts": verts}
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
    done = missed = 0
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
