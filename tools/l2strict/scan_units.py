#!/usr/bin/env python3
"""Scan a L2 static mesh bulk for the 29-B section units: [01][XX][YY]
[81 81][2 verts x 12 B]. The units = the section rectangles (the diagonal
corners), the plate's surface pieces. Usage:
    python3 -m tools.l2strict.scan_units <usx> <MeshName>
"""
import sys, struct
sys.path.insert(0, __file__.rsplit('/', 2)[0])
from l2strict.package import Package
from l2strict.properties import read_object


def scan_units(pkg: Package, want: str) -> list:
    for i in range(pkg.export_count):
        if pkg.class_name_of_export(i) != "StaticMesh":
            continue
        if pkg.name(pkg.exports[i].object_name) != want:
            continue
        e = pkg.exports[i]
        obj = read_object(pkg.data[e.serial_offset:e.serial_offset + e.serial_size],
                          pkg, context=want,
                          has_stack=bool(e.object_flags & 0x02000000))
        bulk = e.serial_offset + obj.end
        d = pkg.data
        end = e.serial_offset + e.serial_size
        units = []
        p = bulk
        while p + 29 <= end:
            if d[p] == 0x01 and d[p + 3] == 0x81 and d[p + 4] == 0x81:
                xx, yy = d[p + 1], d[p + 2]
                vs = struct.unpack_from('<6f', d, p + 5)
                if all(abs(t) < 5000 for t in vs):
                    units.append((xx, yy, vs, p - bulk))
                    p += 29
                    continue
            p += 1
        return units
    return []


def main() -> None:
    pkg_path, want = sys.argv[1], sys.argv[2]
    pkg = Package.from_file(pkg_path)
    units = scan_units(pkg, want)
    print(f"{want}: {len(units)} section units")
    for xx, yy, vs, off in units:
        print(f"  XX={xx:3d} YY={yy:3d} @bulk+{off}: "
              f"v1=({vs[0]:9.2f},{vs[1]:8.2f},{vs[2]:8.2f}) "
              f"v2=({vs[3]:9.2f},{vs[4]:8.2f},{vs[5]:8.2f})")


if __name__ == "__main__":
    main()
