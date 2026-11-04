#!/usr/bin/env python3
"""Extract per-mesh material (texture) lists from decrypted L2 .usx packages.

StaticMesh properties (licensee < 28 packages):
  Materials: type 8 (ARRAY in old packages), no size field, count = compact,
  elements = FStaticMeshMaterial fields WITHOUT None terminator:
    bNoDynamicShadowCast BOOL, EnableCollisionforShadow BOOL,
    EnableCollision BOOL, Material OBJECT
  Repeating property name marks the next element.

Shader objects: Diffuse OBJECT (texture, same package export or import).

Usage: python3 l2_materials.py MAP.json DECRYPTED_DIR OUT.json
"""
import json
import os
import struct
import sys

from l2_probe import Package
from l2_props import _R, read_object


def resolve_ref(pkg, ref):
    """Returns (kind, pkg_file, obj_name, class_name)."""
    if ref == 0:
        return None
    if ref > 0:
        e = pkg.exports[ref - 1]
        return ("export", os.path.splitext(os.path.basename(pkg.path))[0],
                pkg.name(e[3]), pkg.class_of_export(ref - 1))
    imp = -ref - 1
    if not (0 <= imp < len(pkg.imports)):
        return None
    cp, cn, pk, nm = pkg.imports[imp]
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


def parse_staticmesh_materials(pkg, data):
    """Parse properties of a StaticMesh blob (old licensee), return materials list."""
    r = _R(data)
    # properties; StateFrame not present when no HasStack flag — caller passes body
    materials = []
    seen = set()
    elem = None
    while True:
        if r.p >= len(data):
            break
        pos0 = r.p
        ni = r.compact()
        if ni == 0 or pkg.name(ni) == "None":
            break
        nm = pkg.name(ni)
        info = r.u8()
        t = info & 0xF
        st = (info >> 4) & 7
        arr = info >> 7
        if t == 9 and nm == "Materials":
            # ARRAY with size; elements are FStaticMeshMaterial structs w/o None
            if st in (0, 1, 2, 3, 4):
                size = {0: 1, 1: 2, 2: 4, 3: 12, 4: 16}[st]
            elif st == 5:
                size = r.u8()
            elif st == 6:
                size = struct.unpack_from("<H", data, r.p)[0]
                r.p += 2
            else:
                size = struct.unpack_from("<i", data, r.p)[0]
                r.p += 4
            if arr:
                r.compact()  # array index (single-blob form unused here)
            cnt = r.compact()
            end = r.p + size
            elems = []
            for _ in range(cnt):
                cur = {}
                while r.p < end:
                    fni = r.compact()
                    if fni == 0 or pkg.name(fni) == "None":
                        break
                    fname = pkg.name(fni)
                    finfo = r.u8()
                    ft = finfo & 0xF
                    fst = (finfo >> 4) & 7
                    farr = finfo >> 7
                    if fst in (0, 1, 2, 3, 4):
                        fsize = {0: 1, 1: 2, 2: 4, 3: 12, 4: 16}[fst]
                    elif fst == 5:
                        fsize = r.u8()
                    elif fst == 6:
                        fsize = struct.unpack_from("<H", data, r.p)[0]
                        r.p += 2
                    else:
                        fsize = struct.unpack_from("<i", data, r.p)[0]
                        r.p += 4
                    if farr and ft != 3:
                        r.compact()
                    if ft == 3:
                        cur[fname] = bool(farr)
                    elif ft == 5:
                        cur[fname] = r.compact()
                    elif ft == 1:
                        cur[fname] = r.u8()
                    elif ft == 2:
                        cur[fname] = struct.unpack_from("<i", data, r.p)[0]
                        r.p += 4
                    elif ft == 4:
                        cur[fname] = struct.unpack_from("<f", data, r.p)[0]
                        r.p += 4
                    else:
                        r.p += fsize
                        cur[fname] = ("bytes", fsize)
                elems.append(cur)
            r.p = end
            materials = [e.get("Material") for e in elems[:cnt]]
            while len(materials) < cnt:
                materials.append(0)
            seen.update({"Materials"})
        elif t == 8:
            if st == 5:
                r.u8()
            seen.add(nm)
            if arr is False:
                pass
        elif t == 5:
            r.compact()
            seen.add(nm)
        elif t == 4 or t == 2:
            r.p += 4
            seen.add(nm)
        elif t == 1:
            r.u8()
            seen.add(nm)
        elif t == 10:
            sn = pkg.name(r.compact())
            if sn in ("Vector", "Rotator"):
                r.p += 12
            elif sn == "Color":
                r.p += 4
            else:
                r.p += 0
            seen.add(nm)
        else:
            # unknown -> stop (bulk data)
            break
    return materials


def main():
    map_json, dec_dir, out_json = sys.argv[1], sys.argv[2], sys.argv[3]
    d = json.load(open(map_json))

    mesh_pkgs = set(d["packages"].keys())
    result = {}  # mesh package -> {mesh object -> [ (pkg, tex) ] }
    texture_pkgs = {}  # pkg -> set of texture names (for export)

    for pkg_name in sorted(mesh_pkgs):
        path = None
        for sub in ("StaticMeshes",):
            cand = os.path.join(dec_dir, sub, pkg_name + ".usx")
            if os.path.isfile(cand):
                path = cand
                break
        if not path:
            print(f"skip {pkg_name}: no decrypted usx")
            continue
        try:
            p = Package(path)
        except Exception as e:
            print(f"skip {pkg_name}: {e}")
            continue
        meshes = {}
        used_objs = set(d["packages"][pkg_name])
        for i in range(p.export_count):
            cls, sup, pk, nm, fl, size, off = p.exports[i]
            oname = p.name(nm)
            if p.class_of_export(i) != "StaticMesh" or oname not in used_objs:
                continue
            data = p.data[off:off + size]
            try:
                mats = parse_staticmesh_materials(p, data)
            except Exception as e:
                mats = []
            texlist = []
            for mref in mats:
                if not isinstance(mref, int) or mref == 0:
                    texlist.append(None)
                    continue
                rr = resolve_ref(p, mref)
                if rr is None:
                    texlist.append(None)
                    continue
                kind, pkgf, oname2, cls2 = rr
                if cls2 == "Shader":
                    # find Shader object and resolve Diffuse
                    sh = find_shader_diffuse(path, p, oname2)
                    if sh:
                        texlist.append(sh)
                    else:
                        texlist.append((pkgf, oname2))
                else:
                    texlist.append((pkgf, oname2))
            meshes[oname] = texlist
        result[pkg_name] = meshes
        print(f"{pkg_name}: {len(meshes)} meshes")

    json.dump(result, open(out_json, "w"), indent=1)
    print("saved", out_json)


def find_shader_diffuse(usx_path, pkg, shader_name):
    """Locate a Shader by name in the SAME package file, return (pkg, tex)."""
    p = pkg
    for i in range(p.export_count):
        cls, sup, pk, nm, fl, size, off = p.exports[i]
        if p.name(nm) != shader_name:
            continue
        if p.class_of_export(i) != "Shader":
            return None
        data = p.data[off:off + size]
        r = _R(data)
        while r.p < len(data) - 1:
            ni = r.compact()
            if ni == 0:
                break
            fname = p.name(ni)
            info = r.u8()
            t = info & 0xF
            st = (info >> 4) & 7
            arr = info >> 7
            if t == 5:
                ref = r.compact()
                if fname == "Diffuse":
                    rr = resolve_ref(p, ref)
                    if rr:
                        return (rr[1], rr[2])
            elif t == 3:
                if st == 5:
                    r.u8()
            elif t == 4 or t == 2:
                r.p += 4
            elif t == 1:
                r.u8()
            elif t == 10:
                r.compact()
                sn = p.name(0) if False else None
                r.p += 12 if True else 0
            else:
                break
    return None


if __name__ == "__main__":
    main()
