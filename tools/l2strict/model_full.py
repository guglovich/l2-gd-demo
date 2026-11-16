#!/usr/bin/env python3
"""Full L2 level-Model walk (UModel::Serialize, ver 123 / licensee 23), per
the _L2_UNREALED reference (Source_UnrealED/src/Engine/Src/UnModel.cpp +
Inc/UnModel.h + Inc/L2ModelReader.h, read 2026-11-16).

The old levelbsp.py walk stopped after the Verts array: it never validated
the tail (Zones/Polys/Bounds/Leaves/Sections/LightMaps/L2Lighting) and never
checked the export end. The reference gives the exact load order:

  Super::Serialize   props + FBox(Min,Max,IsValid BYTE = 25 B) + FSphere 16 B
  TTransArray Vectors, Points, Nodes, Surfs, Verts   (plain TArray on load)
  INT NumSharedSides, INT NumZones
  Zones[i]  x NumZones  (compact ZoneActor + QWORD + QWORD + FLOAT)
  compact Polys ref
  TArray<FBox> Bounds (25 B each) + TArray<INT> LeafHulls + TArray<FLeaf>
    Leaves (3 compacts + QWORD) + TArray<compact> Lights
  INT RootOutside + INT Linked
  TArray<FBspSection> Sections (ver>=105): each =
      FBspVertexStream: TArray<FBspVertex> (40 B each at ver>=109:
        Position 12 + U,V 8 + U2,V2 8 + Normal 12) + QWORD CacheId + INT Rev
      + compact Material + INT NumNodes + DWORD PolyFlags + INT iLightMapTex
  TArray<FLightMap> LightMaps (ver>=105): each = 7 compacts + FMatrix 64 B
      + 3 FVector 36 B + TArray<FLightBitmap> Bitmaps (compact LightActor +
      TArray BYTE Bits + INT SizeX,SizeY + INT Stride + INT MinX,MinY,MaxX,
      MaxY) + compact Level + INT Revision
  ReadL2ModelLighting (IsL2MeshLoad: ver 123..133, licensee 16..40):
      Groups = compact
      per group: Variants = compact; per variant = ReadL2LightTexture:
          compact Level ref
          Count = compact; Count x INT (light-map indices)
          QWORD CacheId + INT Revision
          2 mips: INT MipEnd + compact Count + Count bytes
          INT Format + INT Width + INT Height + INT Revision
          (licensee 23: no per-group owner ref, no trailing atlas dims)
  L2MeshRequireEnd: the walk must land EXACTLY on the export end.

Diagnostics printed per stage; the temple-region report answers whether the
Shillien Temple stairs live in the level Model (and were lost to the
MAX_SPAN=7000 filter) or not.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_probe import Package  # noqa: E402
from levelbsp import find_level_model, read_compact  # noqa: E402


def dump_field(label, p, count, size, end):
    print(f"  {label}: count={count} at {p}..{p + count * size} "
          f"(next {end})")


def walk_model(d, p, end):
    """Walk the reference UModel::Serialize order; return a dict of arrays."""
    stages = {}

    def fail(msg):
        raise ValueError(f"{msg} (at {p}/{end}, stages: {list(stages)})")

    # ---- 5 TTransArrays -------------------------------------------------
    n, p = read_compact(d, p)
    vec = [struct.unpack_from("<3f", d, p + i * 12) for i in range(n)]
    p += n * 12
    stages["vectors"] = n

    n, p = read_compact(d, p)
    pts = [struct.unpack_from("<3f", d, p + i * 12) for i in range(n)]
    p += n * 12
    stages["points"] = n

    nn, p = read_compact(d, p)
    nodes = []
    for _ in range(nn):
        plane = struct.unpack_from("<4f", d, p)
        q = p + 16 + 8 + 1          # plane + ZoneMask + NodeFlags(BYTE)
        cs = []
        for _ in range(7):          # iVertPool,iSurf,3 children,2 bounds
            v, q = read_compact(d, q)
            cs.append(v)
        q += 16 + 16                # two spheres
        z0 = d[q]
        z1 = d[q + 1]
        nvert = d[q + 2]            # iZone[0], iZone[1], NumVertices = 3 bytes;
        q += 3                      # NodeFlags was consumed BEFORE iVertPool
        ileaf = []
        for _ in range(2):
            v, q = read_compact(d, q)
            ileaf.append(v)
        sect = []
        for _ in range(3):          # iSection, iFirstVertex, iLightMap
            v, q = read_compact(d, q)
            sect.append(v)
        nodes.append({"plane": plane, "cs": cs, "zone": (z0, z1),
                      "nvert": nvert, "ileaf": ileaf, "sect": sect,
                      "start": p, "end": q})
        p = q
    stages["nodes"] = nn

    nsurf, p = read_compact(d, p)
    surfs = []
    for _ in range(nsurf):
        mat, p = read_compact(d, p)
        flags = struct.unpack_from("<I", d, p)[0]
        p += 4
        idx = []
        for _ in range(5):
            v, p = read_compact(d, p)
            idx.append(v)
        _, p = read_compact(d, p)   # owner Brush objref
        plane = struct.unpack_from("<4f", d, p)
        p += 16 + 4                 # FPlane + LightMapScale
        p += 4                      # L2SurfaceExtension (licensee 23..40)
        surfs.append({"mat": mat, "flags": flags, "idx": idx, "plane": plane})
    stages["surfs"] = nsurf

    nvert, p = read_compact(d, p)
    verts = []
    for _ in range(nvert):
        iv, p = read_compact(d, p)
        isd, p = read_compact(d, p)
        verts.append((iv, isd))
    stages["verts"] = nvert

    # ---- NumSharedSides + NumZones + Zones ------------------------------
    nsh = struct.unpack_from("<i", d, p)[0]
    p += 4
    nz = struct.unpack_from("<i", d, p)[0]
    p += 4
    if not (0 <= nz <= 64):
        fail(f"bad NumZones {nz}")
    stages["num_shared_sides"] = nsh
    stages["num_zones"] = nz
    zones = []
    for _ in range(nz):
        za, p = read_compact(d, p)
        conn, vis, lr = struct.unpack_from("<QQf", d, p)
        p += 20
        zones.append({"actor": za})
    stages["zones"] = nz

    # ---- Polys ref -------------------------------------------------------
    polys, p = read_compact(d, p)
    stages["polys"] = polys

    # ---- Bounds / LeafHulls / Leaves / Lights ---------------------------
    nb, p = read_compact(d, p)
    p += nb * 25
    stages["bounds"] = nb
    nlh, p = read_compact(d, p)
    p += nlh * 4
    stages["leafhulls"] = nlh
    nl, p = read_compact(d, p)
    for _ in range(nl):
        for _ in range(3):
            _, p = read_compact(d, p)
        p += 8
    stages["leaves"] = nl
    nli, p = read_compact(d, p)
    for _ in range(nli):
        _, p = read_compact(d, p)
    stages["lights"] = nli

    ro, lk = struct.unpack_from("<ii", d, p)
    p += 8
    stages["root_outside"] = ro
    stages["linked"] = lk

    # ---- Sections (ver>=105) --------------------------------------------
    nsec, p = read_compact(d, p)
    sections = []
    for _ in range(nsec):
        nv, p = read_compact(d, p)
        q = p + nv * 40
        cache = struct.unpack_from("<Q", d, q)[0]
        q += 8
        rev = struct.unpack_from("<i", d, q)[0]
        q += 4
        mat, q = read_compact(d, q)
        numnodes = struct.unpack_from("<i", d, q)[0]
        q += 4
        pflags = struct.unpack_from("<I", d, q)[0]
        q += 4
        ilm = struct.unpack_from("<i", d, q)[0]
        q += 4
        sections.append({"nvert": nv, "material": mat, "num_nodes": numnodes,
                         "poly_flags": pflags, "ilm": ilm, "vstart": p})
        p = q
    stages["sections"] = nsec

    # ---- LightMaps (ver>=105) -------------------------------------------
    nlm, p = read_compact(d, p)
    for _ in range(nlm):
        for _ in range(7):
            _, p = read_compact(d, p)
        p += 64 + 36                # FMatrix + LightMapBase/X/Y
        nbit, p = read_compact(d, p)
        for _ in range(nbit):
            _, p = read_compact(d, p)   # LightActor
            nbits, p = read_compact(d, p)
            p += nbits
            p += 8 + 4 + 16         # SizeX,SizeY,Stride,MinX,MinY,MaxX,MaxY
        _, p = read_compact(d, p)   # Level
        p += 4                      # Revision
    stages["lightmaps"] = nlm

    # ---- ReadL2ModelLighting (IsL2MeshLoad: 123..133/16..40) -------------
    groups, p = read_compact(d, p)
    if groups < 0 or groups > 4096:
        fail(f"bad lighting group count {groups}")
    stages["lighting_groups"] = groups
    for _ in range(groups):
        variants, p = read_compact(d, p)
        if not (1 <= variants <= 64):
            fail(f"bad variant count {variants}")
        for _ in range(variants):
            _, p = read_compact(d, p)   # Level ref
            cnt, p = read_compact(d, p)
            if not (0 <= cnt <= (end - p) // 4):
                fail(f"bad light-map index count {cnt}")
            p += cnt * 4
            p += 8 + 4              # CacheId + Revision
            for _ in range(2):
                mipend = struct.unpack_from("<i", d, p)[0]
                p += 4
                mcnt, p = read_compact(d, p)
                if mcnt != 0 and mipend != p + mcnt:
                    fail(f"mip boundary {mipend} != {p}+{mcnt}")
                p += mcnt
            fmt, w, h, rev = struct.unpack_from("<iiii", d, p)
            if not ((w == 0 and h == 0) or (0 < w <= 8192 and 0 < h <= 8192)):
                fail(f"bad light texture dims {w}x{h}")
            p += 16
        nidx, p = read_compact(d, p)
        if not (0 <= nidx <= (end - p) // 4):
            fail(f"bad group index count {nidx}")
        p += nidx * 4

    return {"stages": stages, "vec": vec, "pts": pts, "nodes": nodes,
            "surfs": surfs, "verts": verts, "zones": zones, "sections": sections,
            "end": p, "export_end": end}


def main():
    map_path = sys.argv[1] if len(sys.argv) > 1 else "tmp/decrypted/MAPS/20_18.unr"
    pkg = Package(map_path)
    midx = find_level_model(pkg)
    e = pkg.exports[midx]
    off, size = e[6], e[5]
    d = pkg.data[off:off + size]
    print(f"level model export {midx}: {size} bytes at {off}")
    M = walk_model(d, 1 + 25 + 16, size)
    s = M["stages"]
    print("stages:", json.dumps(s, indent=1))
    print(f"END: walk={M['end']} export_end={M['export_end']} "
          f"{'EXACT (L2MeshRequireEnd ok)' if M['end'] == M['export_end'] else '*** MISMATCH ' + str(M['export_end'] - M['end']) + ' bytes ***'}")

    # temple region probe: which surfs/nodes cover X 27000..30000,
    # Y 11000..14000, Z -6000..-1500?
    X0, X1, Y0, Y1, Z0, Z1 = 24000, 32000, 10000, 16000, -6000, -1500
    near_s = []
    for si, sf in enumerate(M["surfs"]):
        ni = sf["idx"][4] if len(sf["idx"]) == 5 else None
        if ni is None or not (0 <= ni < len(M["nodes"])):
            continue
        nd = M["nodes"][ni]
        pool, cnt = nd["cs"][0], nd["nvert"]
        if cnt < 3 or pool + cnt > len(M["verts"]):
            continue
        poly = []
        ok = True
        for k in range(cnt):
            vi = M["verts"][pool + k][0]
            if not (0 <= vi < len(M["pts"])):
                ok = False
                break
            poly.append(M["pts"][vi])
        if not ok:
            continue
        xs = [v[0] for v in poly]
        ys = [v[1] for v in poly]
        zs = [v[2] for v in poly]
        if max(xs) >= X0 and min(xs) <= X1 and max(ys) >= Y0 \
                and min(ys) <= Y1 and max(zs) >= Z0 and min(zs) <= Z1:
            near_s.append((si, sf["mat"], sf["flags"], cnt,
                           round(min(xs)), round(max(xs)),
                           round(min(ys)), round(max(ys)),
                           round(min(zs)), round(max(zs))))
    print(f"temple-region surfs (X {X0}..{X1} Y {Y0}..{Y1} Z {Z0}..{Z1}): "
          f"{len(near_s)}")
    for row in near_s[:40]:
        print("   surf", row)
    json.dump({"stages": s, "end": M["end"], "export_end": M["export_end"],
               "temple_surfs": near_s},
              open("tmp/model_full_report.json", "w"), indent=1)


if __name__ == "__main__":
    main()
