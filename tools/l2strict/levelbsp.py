#!/usr/bin/env python3
"""Render the LEVEL BSP directly from the decrypted map's level Model.

The brush reconstruction (bsp2.py) misses the CSG-split faces: the level
Model (found via Level -> compact ref) carries the engine's own merged
geometry — Surfs + Nodes + the FVert pool. RE 2026-11-12 (fnd_13/14/15):

  Model file layout: props(None) + FBox(25 B) + 4 dwords
    + Vectors TArray + Points TArray + Nodes TArray + Surfs TArray
    + Verts TArray (compact pairs: iVertex, iSide) + ints + 24-B stream + ...

  FBspSurf file record: objref MATERIAL, dword PolyFlags, 5 compacts
  [pBase(point), pNormal(vec), pTextureU(vec), pTextureV(vec), iBspNode],
  objref owner Brush, 16-B plane, float lightmap scale, int.

  FBspNode file record: 4 floats (the plane inline), 2 ints, 1 byte,
  7 compacts (c0 = iVertexPool, c4 = iSurf), 16 B + 16 B, 3 bytes
  (byte[2] = NumVertices!), 2 ints, 3 ints.

  The surf's polygon = Points[Verts[pool .. pool+NumVertices].iVertex].
  Validated: 774/774 surf polygons lie on their node planes.

  UVs: u = dot(P - pBase, pTextureU) in TEXELS (|pU| = 0.5..4 = the UE
  editor texel scale); world.gd scales by 1/texture_size per material.

Output (into ASSET_DIR):
  meshes_bsp/LevelBSP.gltf/.bin — one surface per material, meters, Godot axes
  levelbsp.json — {"surfaces": [{"tex": [pkg, obj] | null}]}
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_probe import Package  # noqa: E402

# The temple street = TWO GIANT CSG-merged DE_V_floor01 slabs spanning 3882
# and 5041 units (x 6343..10225 / 9836..14877) — the earlier MAX_SPAN 3500
# misread them as the zone separators and dropped the street floors. The REAL
# zone/sky separator boxes span 7.4k-11k units (bsp2 measurement), so 7000
# keeps the street slabs and still drops the zone boxes.
MAX_SPAN = 7000.0


def read_compact(d, p):
    """The authentic L2 FCompactIndex decode (Core.dll 0x1015cfb0, fnd_13):
    sign = bit 0x80 of the FIRST byte; magnitude = (b0 & 0x3F) | (cont << 6).
    Negative multi-byte values (first byte 0xC0|low6) decode negative."""
    b0 = d[p]
    p += 1
    mag = b0 & 0x3F
    if b0 & 0x40:
        sh = 6
        while True:
            b = d[p]
            p += 1
            mag |= (b & 0x7F) << sh
            sh += 7
            if not b & 0x80:
                break
    return (-mag if b0 & 0x80 else mag), p


def resolve_tex(pkg, ref, shaders):
    """Resolve an object ref to a staged [package, object] texture pair."""
    if not isinstance(ref, int) or ref == 0:
        return None
    if ref > 0:
        j = ref - 1
        if j >= pkg.export_count:
            return None
        cls = pkg.class_of_export(j)
        nm = pkg.name(pkg.exports[j][3])
        if cls == "Texture":
            return [None, nm]
        if cls == "Shader":
            diff = shaders.get(f"::{nm}") or shaders.get(nm)
            if diff:
                return [None, diff]
        return None
    imp = -ref - 1
    if not (0 <= imp < len(pkg.imports)):
        return None
    cp, cn, pk, nm = pkg.imports[imp]
    cls = pkg.name(cn)
    obj = pkg.name(nm)
    pkg_file = None
    cur = pk
    while cur != 0:
        if cur > 0:
            pkg_file = pkg.name(pkg.exports[cur - 1][3])
            break
        imp2 = -cur - 1
        if not (0 <= imp2 < len(pkg.imports)):
            break
        o_cp, o_cn, o_pk, o_nm = pkg.imports[imp2]
        pkg_file = pkg.name(o_nm)
        if pkg.name(o_cn) == "Package":
            break
        cur = o_pk
    if cls == "Texture":
        return [pkg_file.lower() if pkg_file else pkg_file, obj]
    if cls == "Shader":
        diff = shaders.get(f"{pkg_file}::{obj}") if pkg_file else None
        if diff:
            return [pkg_file.lower() if pkg_file else pkg_file, diff]
    return None


SCALE = 0.01


def find_level_model(pkg):
    best = None
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) != "Level":
            continue
        fl, size, off = pkg.exports[i][4], pkg.exports[i][5], pkg.exports[i][6]
        d = pkg.data[off:off + size]
        p = 0
        while p < len(d):
            try:
                v, q = read_compact(d, p)
            except IndexError:
                break
            if v > 0:
                j = v - 1
                if j < pkg.export_count and pkg.class_of_export(j) == "Model" \
                        and pkg.exports[j][5] > 100:
                    if best is None or pkg.exports[j][5] > pkg.exports[best][5]:
                        best = j
            p = q if q > p else p + 1
    return best


def parse_level_model(pkg, midx):
    off, size = pkg.exports[midx][6], pkg.exports[midx][5]
    d = pkg.data[off:off + size]
    p = 1 + 25 + 16  # props(None) + FBox(Min,Max,IsValid) + 4 dwords
    n, p = read_compact(d, p)
    vec = [struct.unpack_from("<3f", d, p + i * 12) for i in range(n)]
    p += n * 12
    n2, p = read_compact(d, p)
    pts = [struct.unpack_from("<3f", d, p + i * 12) for i in range(n2)]
    p += n2 * 12
    nn, p = read_compact(d, p)

    def node_fields(p):
        q = p
        plane = struct.unpack_from("<4f", d, q)
        q += 16 + 8 + 1
        cs = []
        for _ in range(7):
            v, q = read_compact(d, q)
            cs.append(v)
        q += 16 + 16
        nvert = d[q + 2]
        q += 3 + 8 + 12
        # the 5 fixed INTs: iLeaf0, iLeaf1, iSection, iFirstVertex, iLightMap
        sect = struct.unpack_from("<3i", d, q - 12)
        return {"cs": cs, "nvert": nvert, "sect": sect, "plane": plane,
                "end": q}

    nodes = []
    for _ in range(nn):
        nd = node_fields(p)
        nodes.append(nd)
        p = nd["end"]
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
        _, p = read_compact(d, p)  # the owner Brush objref (variable length)
        p += 24  # 16-B plane + float lightmap scale + int
        surfs.append({"mat": mat, "flags": flags, "idx": idx})
    nvert, p = read_compact(d, p)
    verts = []
    for _ in range(nvert):
        iv, p = read_compact(d, p)
        isd, p = read_compact(d, p)
        verts.append((iv, isd))
    sections = parse_sections(d, p, nodes, surfs)
    return {"vec": vec, "pts": pts, "nodes": nodes, "surfs": surfs,
            "verts": verts, "sections": sections}


def parse_sections(d, p, nodes, surfs):
    """Walk NumSharedSides..Sections and decode the client's baked section
    vertex streams (2026-11-18). Each FBspSection = compact NumVertices +
    [NumVertices x 40 B records: pos12 + uv8 + 8 B mystery + normal12] +
    INT Revision + compact Material objref + INT NumNodes + DWORD PolyFlags
    + INT iLightMapTexture. Validation (this model): Revision == NumNodes
    == the node count of the section, and the section material == the
    materials of its nodes' surfs — 31/31 sections. The stream UVs are the
    client's FINAL texture coordinates (tile units, repeat) — the computed
    dot(v-base,U) texel UVs are wrong by orders of magnitude and produced
    every flat-gray BSP patch (the 'gray rectangles')."""
    nsh = struct.unpack_from("<i", d, p)[0]
    p += 4
    nz = struct.unpack_from("<i", d, p)[0]
    p += 4
    if not (0 <= nz <= 64):
        raise ValueError(f"bad NumZones {nz}")
    for _ in range(nz):
        _, p = read_compact(d, p)
        p += 20
    _, p = read_compact(d, p)          # Polys objref
    nb, p = read_compact(d, p)
    p += nb * 25
    nlh, p = read_compact(d, p)
    p += nlh * 4
    nl, p = read_compact(d, p)
    for _ in range(nl):
        for _ in range(3):
            _, p = read_compact(d, p)
        p += 8
    nli, p = read_compact(d, p)
    for _ in range(nli):
        _, p = read_compact(d, p)
    p += 8                              # RootOutside + Linked

    nsec, p = read_compact(d, p)
    node_count = {}
    for nd in nodes:
        k = nd["sect"][0]
        node_count[k] = node_count.get(k, 0) + 1
    sections = []
    for _ in range(nsec):
        nv, after = read_compact(d, p)
        vstart = after
        p = after + nv * 40
        rev = struct.unpack_from("<i", d, p)[0]
        p += 4
        mat, p = read_compact(d, p)
        numnodes = struct.unpack_from("<i", d, p)[0]
        p += 4
        pflags = struct.unpack_from("<I", d, p)[0]
        p += 4
        ilm = struct.unpack_from("<i", d, p)[0]
        p += 4
        recs = []
        for i in range(nv):
            o = vstart + i * 40
            pos = struct.unpack_from("<3f", d, o)
            uv = struct.unpack_from("<2f", d, o + 12)
            recs.append((pos, uv))
        if rev != numnodes or numnodes != node_count.get(len(sections), 0):
            raise ValueError(
                f"section {len(sections)}: rev {rev} numnodes {numnodes} "
                f"vs node count {node_count.get(len(sections), 0)}")
        sections.append({"nvert": nv, "mat": mat, "num_nodes": numnodes,
                         "poly_flags": pflags, "ilm": ilm, "verts": recs})
    return sections


def main():
    map_path, asset_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    pkg = Package(map_path)
    shaders = json.load(open(os.path.join(asset_dir, "shader_diffuse.json")))

    midx = find_level_model(pkg)
    if midx is None:
        print("no level Model found")
        return
    M = parse_level_model(pkg, midx)
    print(f"level model export {midx}: {len(M['vec'])} vecs, {len(M['pts'])} pts, "
          f"{len(M['nodes'])} nodes, {len(M['surfs'])} surfs, {len(M['verts'])} verts")

    vec, pts, nodes, verts = M["vec"], M["pts"], M["nodes"], M["verts"]
    os.makedirs(out_dir, exist_ok=True)

    # group the renderable surfs by resolved texture; each group = a surface
    groups = {}          # tex_key -> list of polygons [(verts3d, uvs)]
    stats = {"hidden": 0, "marker": 0, "span": 0, "nomat": 0, "drawn": 0}
    surf_tex_of_group = {}
    for s in M["surfs"]:
        tex = resolve_tex(pkg, s["mat"], shaders)
        if s["flags"] & (0x1 | 0x80 | 0x4000000):
            stats["hidden"] += 1
            continue
        if tex and tex[1] in ("AntiPortal", "ZonePortal"):
            stats["marker"] += 1
            continue
        if not tex:
            stats["nomat"] += 1
            continue
        ni = s["idx"][4]
        if not (0 <= ni < len(nodes)):
            stats["nomat"] += 1
            continue
        nd = nodes[ni]
        pool, cnt = nd["cs"][0], nd["nvert"]
        if cnt < 3 or pool + cnt > len(verts):
            stats["nomat"] += 1
            continue
        poly = []
        ok = True
        for k in range(cnt):
            vi = verts[pool + k][0]
            if not (0 <= vi < len(pts)):
                ok = False
                break
            poly.append(pts[vi])
        if not ok:
            stats["nomat"] += 1
            continue
        xs = [v[0] for v in poly]
        ys = [v[1] for v in poly]
        if (max(xs) - min(xs)) > MAX_SPAN or (max(ys) - min(ys)) > MAX_SPAN:
            stats["span"] += 1
            continue
        base = pts[s["idx"][0]]
        U = vec[s["idx"][2]]
        V = vec[s["idx"][3]]
        uvs = []
        for v in poly:
            uvs.append((sum((v[k] - base[k]) * U[k] for k in range(3)),
                        sum((v[k] - base[k]) * V[k] for k in range(3))))
        key = tuple(tex)
        groups.setdefault(key, []).append((poly, uvs, base, U, V))
        surf_tex_of_group[key] = tex
        stats["drawn"] += 1
    print("surfs: drawn %d, hidden %d, marker %d, no-material %d, huge-span %d"
          % (stats["drawn"], stats["hidden"], stats["marker"], stats["nomat"], stats["span"]))

    def _face_normal(verts):
        """Newell's method — robust for polygon fans where the first three
        vertices can be nearly collinear (a cross of v0..v2 is garbage
        there and poisoned the orientation buckets)"""
        nx = ny = nz = 0.0
        n = len(verts)
        for i in range(n):
            a = verts[i]
            b = verts[(i + 1) % n]
            nx += (a[1] - b[1]) * (a[2] + b[2])
            ny += (a[2] - b[2]) * (a[0] + b[0])
            nz += (a[0] - b[0]) * (a[1] + b[1])
        ln = (nx * nx + ny * ny + nz * nz) ** 0.5
        if ln < 1e-9:
            return None
        return (nx / ln, ny / ln, nz / ln)

    def _in_plane(U, V, N):
        """the axes must lie (nearly) in the face plane, else the mapping
        collapses to 1D (the "мусор" stretch)"""
        for A in (U, V):
            ln = sum(x * x for x in A) ** 0.5
            if ln < 1e-9:
                return False
            if abs(sum(A[k] * N[k] for k in range(3)) / ln) > 0.1:
                return False
        return True

    # CANONICAL TEXTURE PROJECTION for the chaotic stone textures (the "стык"
    # fix, same as bsp2.py): all faces of one texture share ONE (U,V)
    # projection through the global origin. 2026-11-14 (the user: "one
    # continuous texture over the whole road"): the phase continuity was not
    # enough — the road plates carried DIFFERENT texel scales of the same
    # texture, and the pattern density jumped at the plate boundaries.
    # The family is chosen per (texture, ORIENTATION CLASS): the faces are
    # bucketed by their quantized face normal, and each orientation class
    # gets its own DOMINANT (U,V). Picking one family per texture globally
    # let a wall family win (floor01: 5 wall faces of 116) and left the
    # horizontal slabs at their own half-scale — the стык on the main road.
    CANON_UV_TEXS = {"DE_V_floor01", "O_dark_01", "DE_V_m12",
                     "oren_sylen_001_1", "DE_V_floor02"}
    for key, entries in groups.items():
        if key[1] not in CANON_UV_TEXS:
            continue
        counts = {}
        axes_of = {}
        for poly, uvs, base, U, V in entries:
            if sum(x * x for x in U) < 1e-6 or len(poly) < 3:
                continue
            N = _face_normal(poly)
            if N is None or not _in_plane(U, V, N):
                continue
            nk = tuple(round(x, 1) for x in N)
            dk = (tuple(round(x, 3) for x in U), tuple(round(x, 3) for x in V))
            ck = (nk, dk)
            counts[ck] = counts.get(ck, 0) + 1
            axes_of.setdefault(ck, (U, V))
        if not counts:
            continue
        # dominant (U,V) per orientation bucket
        best = {}
        for (nk, dk), c in counts.items():
            if c > best.get(nk, (0, None))[0]:
                best[nk] = (c, dk)
        print(f"  canon {key[1]}: {len(best)} orientation classes: "
              + ", ".join(f"{nk} -> {dk[0]}x{dk[1]} (n={c})"
                          for nk, (c, dk) in sorted(best.items(),
                                                    key=lambda kv: str(kv[0]))))
        new_entries = []
        for poly, uvs, base, U, V in entries:
            Uc, Vc = U, V
            if len(poly) >= 3:
                N = _face_normal(poly)
                if N is not None:
                    nk = tuple(round(x, 1) for x in N)
                    if nk in best:
                        cand = axes_of[(nk, best[nk][1])]
                        if _in_plane(cand[0], cand[1], N):
                            Uc, Vc = cand
            nuvs = []
            for v in poly:
                nuvs.append((sum(v[k] * Uc[k] for k in range(3)),
                             sum(v[k] * Vc[k] for k in range(3))))
            new_entries.append((poly, nuvs, (0.0, 0.0, 0.0), Uc, Vc))
        groups[key] = new_entries

    # build the glTF: one primitive per texture group
    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    mesh_prims = []
    surfaces = []
    for key in sorted(groups.keys()):
        tex = surf_tex_of_group[key]
        si = len(mesh_prims)
        pos = []
        uvs = []
        idx = []
        vbase = 0
        for poly, uv, _base, _U, _V in groups[key]:
            for v in poly:
                pos.extend([v[0] * SCALE, v[2] * SCALE, v[1] * SCALE])
            # BOTH components per vertex: the old `uvs.extend([u for u, w in
            # uv])` dropped V, leaving the UV accessor at HALF the vertex
            # count — vertices read mis-paired UVs (the LevelBSP slabs
            # sampled garbage wherever they were visible, DEVLOG-41/42).
            for u, w in uv:
                uvs.extend([u, w])
            n = len(poly)
            for k in range(1, n - 1):
                idx.extend([vbase, vbase + k + 1, vbase + k])
            vbase += n
        if not idx:
            continue
        pb = struct.pack(f"<{len(pos)}f", *pos)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(pb)})
        blob.extend(pb)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                          "count": len(pos) // 3, "type": "VEC3",
                          "min": [min(pos[0::3]), min(pos[1::3]), min(pos[2::3])],
                          "max": [max(pos[0::3]), max(pos[1::3]), max(pos[2::3])]})
        ub = struct.pack(f"<{len(uvs)}f", *uvs)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(ub)})
        blob.extend(ub)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                          "count": len(uvs) // 2, "type": "VEC2"})
        ib = struct.pack(f"<{len(idx)}I", *idx)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(ib)})
        blob.extend(ib)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5125,
                          "count": len(idx), "type": "SCALAR"})
        while len(blob) % 4:
            blob.append(0)
        materials.append({"name": f"m{si}", "pbrMetallicRoughness":
                          {"baseColorFactor": [0.4, 0.4, 0.4, 1.0]},
                          "doubleSided": True})
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 3,
                                          "TEXCOORD_0": len(accessors) - 2},
                           "indices": len(accessors) - 1, "material": si, "mode": 4})
        surfaces.append({"tex": list(tex)})

    gltf = {
        "asset": {"version": "2.0", "generator": "l2godot levelbsp"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "LevelBSP"}],
        "meshes": [{"name": "LevelBSP", "primitives": mesh_prims}],
        "materials": materials,
        "accessors": accessors, "bufferViews": buffer_views,
        "buffers": [{"uri": "LevelBSP.bin", "byteLength": len(blob)}],
    }
    json.dump(gltf, open(os.path.join(out_dir, "LevelBSP.gltf"), "w"))
    open(os.path.join(out_dir, "LevelBSP.bin"), "wb").write(bytes(blob))
    json.dump({"schema": 1, "surfaces": surfaces},
              open(os.path.join(asset_dir, "levelbsp.json"), "w"), indent=1)
    print(f"LevelBSP: {len(mesh_prims)} surfaces, {len(blob)} bytes")


if __name__ == "__main__":
    main()
