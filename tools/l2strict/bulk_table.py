#!/usr/bin/env python3
"""Per-mesh table of the export-tail box and the byte right after it.

For every ``StaticMesh`` export of a package, read the 6 floats at
``serial_offset + props.end`` as a box (min.xyz, max.xyz) and print the
4 bytes that follow. Two checks run on the same data:

* ``box_ok`` - ``min <= max`` on all three axes. A true ``FBox`` must pass;
  a misaligned read usually does not (it does not prove the box is the
  render bounds, only that the six floats are one consistent interval).
* ``after24`` - the byte at box start + 24 across the whole package. If it
  is a fixed value on every mesh, it is a record marker, not a field.

Usage:

    python3 -m tools.l2strict.bulk_table <usx>

Read-only: nothing is written back to the package or the assets.
"""
import struct
import sys

from .package import Package
from .properties import read_object


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2:
        print("usage: python3 -m tools.l2strict.bulk_table <usx>",
              file=sys.stderr)
        return 2
    pkg = Package.from_file(argv[1])
    data = pkg.data

    rows = []
    for idx in range(pkg.export_count):
        if pkg.class_name_of_export(idx) != "StaticMesh":
            continue
        exp = pkg.exports[idx]
        end = exp.serial_offset + exp.serial_size
        seg = data[exp.serial_offset:end]
        props = read_object(seg, pkg, context="mesh",
                            has_stack=bool(exp.object_flags & 0x02000000))
        pe = exp.serial_offset + props.end
        rows.append((pkg.name(exp.object_name), exp.serial_size,
                     pe, end - pe, data))

    print("%-24s %-9s %-8s %-6s %s" % (
        "mesh", "size", "props_end", "tail", "box / marker"))
    ok = 0
    for nm, size, pe, tail, d in rows:
        if pe + 24 > pe + tail:
            print("%-24s %-9d %-8d %-6d SHORT" % (nm, size, pe, tail))
            continue
        mn = struct.unpack_from("<3f", d, pe)
        mx = struct.unpack_from("<3f", d, pe + 12)
        okbox = all(mn[i] <= mx[i] for i in range(3))
        if okbox:
            ok += 1
        after = d[pe + 24:pe + 28].hex(" ")
        print("%-24s %-9d %-8d %-6d %-5s %s | %s" % (
            nm, size, pe, tail, okbox,
            " ".join("%.1f" % v for v in mn),
            " ".join("%.1f" % v for v in mx)))
        print("%-24s %-9s %-8s %-6s %s" % ("", "", "", "", after))
    print()
    print("boxes ok: %d / %d" % (ok, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
