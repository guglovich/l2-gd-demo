#!/usr/bin/env python3
"""Probe Lineage 2 (UE2 NC-modified) package files.

L2 package format (verified on 23_14.unr, ver 123/28):
  summary: tag u32, ver u16, licensee u16, flags i32,
           nameCount/nameOffset, exportCount/exportOffset,
           importCount/importOffset, GUID 16 bytes
  names:   u8 len incl NUL (0xFF => int32 signed len, UTF-16), bytes, u32 flags
  imports: ClassPackage compact, ClassName compact, PackageIndex i32, ObjectName compact
  exports: ClassIndex compact, SuperIndex compact, PackageIndex i32, ObjectName compact,
           ObjectFlags u32, SerialSize compact, SerialOffset compact (if size>0)

Usage:
  python3 l2_probe.py FILE [--names PATTERN] [--classes] [--class NAME] [--imports]
"""
import struct
import sys


class Reader:
    def __init__(self, data, pos=0):
        self.d = data
        self.p = pos

    def u8(self):
        b = self.d[self.p]
        self.p += 1
        return b

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def compact(self):
        b = self.u8()
        sign = b & 0x80
        r = b & 0x3F
        sh = 6
        if b & 0x40:
            while True:
                b = self.u8()
                r |= (b & 0x7F) << sh
                sh += 7
                if not b & 0x80:
                    break
        return -r if sign else r


class Package:
    def __init__(self, path):
        with open(path, "rb") as fp:
            self.data = fp.read()
        self.path = path
        self._summary()
        self._names()
        self._imports()
        self._exports()

    def _summary(self):
        d = self.data
        self.tag, ver, lic = struct.unpack_from("<IHH", d, 0)
        if self.tag != 0x9E2A83C1:
            raise ValueError(f"bad magic 0x{self.tag:08X}")
        self.ver = ver
        self.licensee = lic
        (self.flags, self.name_count, self.name_offset,
         self.export_count, self.export_offset,
         self.import_count, self.import_offset) = struct.unpack_from("<Iiiiiii", d, 8)

    def _names(self):
        r = Reader(self.data, self.name_offset)
        # name index 0 = first entry ("None"); UE FName indices point here directly
        self.names = []
        for _ in range(self.name_count):
            b0 = r.u8()
            if b0 == 0xFF:
                ln = struct.unpack_from("<i", self.data, r.p)[0]
                r.p += 4
                s = self.data[r.p:r.p + abs(ln) * 2].decode("utf-16-le", "replace")
                r.p += abs(ln) * 2
            else:
                s = self.data[r.p:r.p + b0].split(b"\0")[0].decode("latin-1")
                r.p += b0
            r.u32()
            self.names.append(s)

    def _imports(self):
        r = Reader(self.data, self.import_offset)
        self.imports = []
        for _ in range(self.import_count):
            cp = r.compact()
            cn = r.compact()
            pk = r.i32()
            nm = r.compact()
            self.imports.append((cp, cn, pk, nm))

    def _exports(self):
        r = Reader(self.data, self.export_offset)
        self.exports = []
        for _ in range(self.export_count):
            cls = r.compact()
            sup = r.compact()
            pk = r.i32()
            nm = r.compact()
            fl = r.u32()
            size = r.compact()
            off = r.compact() if size > 0 else 0
            self.exports.append((cls, sup, pk, nm, fl, size, off))

    def name(self, idx):
        return self.names[idx] if 0 < idx < len(self.names) else f"?{idx}"

    def class_of_export(self, idx):
        cls = self.exports[idx][0]
        if cls >= 0:
            return f"(export {cls})"
        imp = -cls - 1
        if 0 <= imp < len(self.imports):
            return self.name(self.imports[imp][3])
        return "?"

    def import_name(self, idx):
        cp, cn, pk, nm = self.imports[idx]
        return f"{self.name(cp)}.{self.name(cn)}:{self.name(nm)}"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    path = args[0]
    pattern = None
    show_classes = False
    only_class = None
    show_imports = False
    i = 1
    while i < len(args):
        if args[i] == "--names":
            i += 1
            pattern = args[i].lower()
        elif args[i] == "--classes":
            show_classes = True
        elif args[i] == "--class":
            i += 1
            only_class = args[i]
        elif args[i] == "--imports":
            show_imports = True
        i += 1

    p = Package(path)
    print(
        f"{path}: ver={p.ver}/{p.licensee} names={p.name_count} "
        f"exports={p.export_count} imports={p.import_count}"
    )

    if pattern:
        hits = [n for n in p.names if pattern in n.lower()]
        print(f"names matching '{pattern}': {len(hits)}")
        for n in hits[:60]:
            print("  ", n)

    if show_imports:
        print("imports:")
        for i, im in enumerate(p.imports):
            print(f"  [{i}] {p.import_name(i)}")

    if show_classes:
        from collections import Counter

        c = Counter(p.class_of_export(i) for i in range(p.export_count))
        print("export classes:")
        for cls, cnt in c.most_common(80):
            print(f"  {cls}: {cnt}")

    if only_class:
        n = 0
        for i in range(p.export_count):
            if p.class_of_export(i) == only_class or (
                only_class in p.class_of_export(i)
            ):
                e = p.exports[i]
                print(f"  [{i}] {p.name(e[3])} size={e[5]} off=0x{e[6]:X}")
                n += 1
                if n >= 50:
                    break
        if n == 0:
            print(f"  (no exports of class {only_class})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
