#!/usr/bin/env python3
"""Full L2 static mesh parser (Interlude 123/12..40), per the _L2_UNREALED
reference serialization (Source_UnrealED/src/Engine/Src/UnStaticMesh.cpp,
UStaticMesh::Serialize L2 branch, 2026-11-16).

Order after the tagged property block (Super::Serialize):
  Sections            TArray<FStaticMeshSection>  (ver>=112: IsStrip BOOL +
                      5 WORDs = 14 B each)
  BoundingBox         FBox = Min,Max (2x12 B) + IsValid BYTE = 25 B
  VertexStream        TArray<FStaticMeshVertex> (24 B each) + INT Revision
  ColorStream         TArray<FColor> (4 B each) + INT Revision
  AlphaStream         TArray<FColor> (4 B each) + INT Revision
  UVStreams           TArray<FStaticMeshUVStream> (TArray<FStaticMeshUV> 8 B
                      each + INT CoordinateIndex + INT Revision)
  IndexBuffer         TArray<WORD> + INT Revision
  WireframeIndexBuffer TArray<WORD> + INT Revision
  CollisionModel      object ref (compact)
  collision           2 spans {INT End, compact Count} when the span probe
                      validates, else OldTriangles TArray (4 FPlanes 64 B +
                      AR_INDEX x4 each) + OldNodes TArray (AR_INDEX x4 +
                      FBox 25 B each) — UnStaticMesh.cpp:371..425
  bStaticMeshLod      BOOL + StaticMeshLod01/02 object refs
  state block         licensee 15..36: 36 B (9 ints; measured [0,0,0,1.0,
                      1.0,0,0,0,0] on all three temple meshes)
  RawEnd INT + compact TriangleCount, then RawTriangles back-to-back
                      (FStaticMeshTriangle: 9 floats verts + INT NumUVs +
                      NumUVs*6 floats + 3 FColors + INT MaterialIndex +
                      DWORD SmoothingMask)
  InternalVersion     INT
  KPhysicsProps       object ref (compact)
  AuthenticationKey   DWORD (ver>=120)
  trailer             to the export end

Verified 2026-11-17 on the three temple meshes — every walk lands EXACTLY
on the export end (L2MeshRequireEnd):
  sylentemple_ent_main  4 sections 316 tris  END 89931/89931
  sylentemple_skin     20 sections 1644 tris END 595877/595877
  sylentemple_side_stair 3 sections (1 empty) 36 tris END 9204/9204

The per-triangle MaterialIndex (INT in each FStaticMeshTriangle) is the
authoritative face-to-material assignment: ent_main {0:40,1:180,2:76,3:20}
matches its four sections exactly, so section i renders Materials(i) —
the identity mapping the reference Build() asserts (UnStaticMesh.cpp:136).
"""
import json
import struct
import sys

import numpy as np

sys.path.insert(0, "tools")
from l2strict.package import Package  # noqa: E402
from l2strict.properties import read_object  # noqa: E402


class Reader:
    def __init__(self, data: bytes, pos: int = 0):
        self.d = data
        self.p = pos

    def u8(self) -> int:
        b = self.d[self.p]
        self.p += 1
        return b

    def u16(self) -> int:
        v = struct.unpack_from("<H", self.d, self.p)[0]
        self.p += 2
        return v

    def i32(self) -> int:
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self) -> float:
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def q64(self) -> int:
        v = struct.unpack_from("<Q", self.d, self.p)[0]
        self.p += 8
        return v

    def raw(self, n: int) -> bytes:
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def compact(self) -> int:
        # the authentic L2 FCompactIndex (Core.dll 0x1015cfb0, fnd_13)
        b0 = self.d[self.p]
        self.p += 1
        mag = b0 & 0x3F
        cont = b0 & 0x40
        sh = 6
        while cont:
            b = self.d[self.p]
            self.p += 1
            mag |= (b & 0x7F) << sh
            sh += 7
            cont = b & 0x80
        return (-(mag + 1) if (b0 & 0x80) else mag)

    def tarray(self, elem: int) -> np.ndarray:
        n = self.compact()
        if n < 0:
            raise ValueError(f"negative TArray count {n} at {self.p}")
        a = np.frombuffer(self.d, dtype=np.uint8, count=n * elem,
                          offset=self.p)
        self.p += n * elem
        return a


def parse_l2_static_mesh(data: bytes, props_end: int, export_end: int,
                         name: str = "") -> dict:
    r = Reader(data, props_end)
    out = {}
    # UPrimitive::Serialize: Super (props) + BoundingBox (FBox = Min, Max,
    # IsValid BYTE = 25 B) + BoundingSphere (FSphere 16 B). The L2 Core FBox
    # IsValid is a BYTE (UnMath.h:1846), measured: 35..60 + 60..76 on the
    # side_stair mesh (the section table lands exactly at +3 sections).
    r.p += 25 + 16
    # Sections
    nsec = r.compact()
    sections = []
    for _ in range(nsec):
        is_strip = r.i32()
        fi, minv, maxv, ntri, nprim = (r.u16() for _ in range(5))
        sections.append({"is_strip": is_strip, "first_index": fi,
                         "min_vertex": minv, "max_vertex": maxv,
                         "num_triangles": ntri, "num_primitives": nprim})
    out["sections"] = sections
    # BoundingBox: FBox = Min(12) + Max(12) + IsValid BYTE = 25 B (the same
    # layout the level-Model walker validated to an exact match; the mesh's
    # own member is read AFTER Sections in the L2 branch).
    r.p += 25
    # VertexStream
    nv = r.compact()
    verts = np.frombuffer(r.raw(nv * 24), dtype=np.float32).reshape(nv, 6)
    r.i32()
    out["vertex_count"] = nv
    out["vertices"] = verts
    # ColorStream + AlphaStream
    nc = r.compact()
    r.raw(nc * 4)
    r.i32()
    na = r.compact()
    r.raw(na * 4)
    r.i32()
    out["color_count"] = nc
    out["alpha_count"] = na
    # UVStreams
    nuvs = r.compact()
    uv_streams = []
    for _ in range(nuvs):
        nuv = r.compact()
        uv = np.frombuffer(r.raw(nuv * 8), dtype=np.float32).reshape(nuv, 2)
        coord = r.i32()
        r.i32()
        uv_streams.append({"coordinate": coord, "uv": uv})
    out["uv_streams"] = uv_streams
    # IndexBuffer + WireframeIndexBuffer
    ni = r.compact()
    indices = np.frombuffer(r.raw(ni * 2), dtype=np.uint16).astype(np.int64)
    r.i32()
    nwf = r.compact()
    r.raw(nwf * 2)
    r.i32()
    out["indices"] = indices
    out["wireframe_count"] = nwf
    # CollisionModel ref
    r.compact()
    # collision: try the span form at this position: INT End + compact Count
    # (the span form's End points INSIDE the export; the array form starts
    # with a compact triangle count). Decide by the reference rule
    # L2HasCollisionSpans — replicate by probing (both arrays must validate).
    save = r.p
    spans_form = False
    try:
        q = save
        ok = True
        for _arr in range(2):
            end0 = struct.unpack_from("<i", d := r.d, q)[0]
            q += 4
            rr = Reader(r.d, q)
            cnt0 = rr.compact()
            q = rr.p
            if not (0 <= cnt0 <= 2000000 and end0 >= q and end0 <= export_end):
                ok = False
                break
            q = end0
        if ok and q <= export_end:
            spans_form = True
    except (IndexError, struct.error):
        pass
    r.p = save
    collision = {"form": "spans" if spans_form else "arrays"}
    if spans_form:
        for arr in range(2):
            end = r.i32()
            cnt = r.compact()
            start = r.p
            collision[f"span{arr}"] = {"end": end, "count": cnt}
            r.p = end
    else:
        # FStaticMeshOldCollisionTriangle = 4 FPlanes (64 B) + AR_INDEX
        # VertexIndices[3] + AR_INDEX(MaterialIndex); FStaticMeshCollisionNode
        # = AR_INDEX x4 + FBox (25 B) — UnStaticMesh.cpp:371..425.
        nt = r.compact()
        collision["old_triangles"] = nt
        for _ in range(nt):
            r.raw(64)
            for _ in range(4):
                r.compact()
        nn = r.compact()
        collision["old_nodes"] = nn
        for _ in range(nn):
            for _ in range(4):
                r.compact()
            r.p += 25
    out["collision"] = collision
    # bStaticMeshLod + Lod refs
    r.i32()
    r.compact()
    r.compact()
    # state block: licensee 15..36 = 36 B (9 ints)
    r.raw(36)
    # RawTriangles
    raw_end = r.i32()
    tri_count = r.compact()
    tris = []
    for _ in range(tri_count):
        v = struct.unpack_from("<9f", data, r.p)
        r.p += 36
        num_uvs = r.i32()
        if num_uvs < 0 or num_uvs > 8:
            raise ValueError(f"bad NumUVs {num_uvs} at {r.p}")
        uvs = []
        for _ in range(num_uvs):
            uvs.append(struct.unpack_from("<6f", data, r.p))
            r.p += 24
        colors = r.raw(12)
        mat = r.i32()
        smooth = struct.unpack_from("<I", data, r.p)[0]
        r.p += 4
        tris.append({"v": v, "uvs": uvs, "material": mat})
    out["raw_triangles"] = tris
    out["raw_end"] = raw_end
    out["tri_count"] = tri_count
    if r.p != raw_end:
        out["warn_raw_end"] = (r.p, raw_end)
    # InternalVersion
    out["internal_version"] = r.i32()
    # KPhysicsProps ref
    r.compact()
    # AuthenticationKey (ver>=120)
    out["auth_key"] = struct.unpack_from("<I", data, r.p)[0]
    r.p += 4
    out["trailer_bytes"] = export_end - r.p
    out["end"] = r.p
    return out


def main() -> None:
    pkg_path, out_path = sys.argv[1], sys.argv[2]
    names = set(sys.argv[3:]) or None
    pkg = Package.from_file(pkg_path)
    results = {}
    for i in range(pkg.export_count):
        if pkg.class_name_of_export(i) != "StaticMesh":
            continue
        e = pkg.exports[i]
        name = pkg.name(e.object_name)
        if names and name not in names:
            continue
        data = pkg.data[e.serial_offset:e.serial_offset + e.serial_size]
        obj = read_object(data, pkg, context=name,
                          has_stack=bool(e.object_flags & 0x02000000))
        res = parse_l2_static_mesh(data, obj.end, e.serial_size, name)
        # material names from the props (the Materials array references)
        mats = obj.props.values.get("Materials") or []
        if not isinstance(mats, list):
            mats = [mats]
        res["props_material_count"] = len(mats)
        results[name] = res
        tris = res["raw_triangles"]
        by_mat = {}
        for t in tris:
            by_mat[t["material"]] = by_mat.get(t["material"], 0) + 1
        mat_names = []
        for m in mats:
            v = m.get("value") if isinstance(m, dict) else None
            mat_names.append(v if isinstance(v, str) else
                             m.get("object", "?") if isinstance(m, dict) else m)
        print(f"{name}: sections={len(res['sections'])} verts={res['vertex_count']} "
              f"raw_tris={res['tri_count']} by_material={by_mat} "
              f"materials={mat_names} trailer={res['trailer_bytes']} "
              f"raw_end_match={'warn ' + str(res['warn_raw_end']) if 'warn_raw_end' in res else 'ok'}")
    json.dump({k: {kk: vv for kk, vv in v.items()
                   if kk not in ("vertices", "uv_streams", "indices")}
               for k, v in results.items()},
              open(out_path, "w"), indent=1, default=str)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
