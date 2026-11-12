#!/usr/bin/env python3
"""Export BSP brush geometry (Polys objects) of a decrypted L2 map, WITH the
authentic per-face textures from the level Model's FBspSurf records.

Outputs (into ASSET_DIR):
  meshes_bsp/BSP_<Polys>.gltf/.bin  — local space, meters, Godot axes
  bsp.json — {schema:2, brushes:[{polys, location, faces}], cover_z}
    faces: [{i, prim, flags, tex}] — i = raw poly index inside the Polys
    object, prim = index into the glTF mesh's surfaces (null = not rendered),
    tex = [package, object] or null.

The texture path (RE 2026-11-12, findings fnd_13/fnd_14):
  Level.myLevel -> the level Model (Model500) -> Surfs[]; each FBspSurf file
  record = {objref MATERIAL, dword PolyFlags, 5 compacts
  [pBase, pNormal, pTextureU, pTextureV, iBrushPoly], objref owner Brush,
  16 B plane, float lightmap scale, int}. Surfs map to brush polys by
  (owner Brush, iBrushPoly = raw poly index). Validated on Brush902/Polys353:
  the street-floor surfs 495-509 carry iBrushPoly 0,1,10..22 and materials
  Oren_DEV_T.DE_V_floor01.

The compact-index decoder (Core.dll ??6@YAAAVFArchive@@AAV0@AAVFCompactIndex@@@Z
@0x1015cfb0): sign = bit 0x80 of the FIRST byte; magnitude = (b0 & 0x3F) |
(continuation << 6). Negatives are NOT -n-1, and negative MULTI-BYTE values
(imports >= 64) exist (first byte = 0xC0|low6). The old decoders misdecoded
every import ref by one and every import >= 64 as positive.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_probe import Package  # noqa: E402
from l2_props import read_object  # noqa: E402

SCALE = 0.01
CELL = 128.0


def read_compact(d, p):
    """The authentic L2 FCompactIndex decode (Core.dll 0x1015cfb0).

    Sign = bit 0x80 of the first byte; magnitude = (b0 & 0x3F) | (cont << 6)
    with 0x80-marked continuation bytes of 7 bits each. Negative multi-byte
    values (first byte 0xC0|low6) decode negative as a whole.
    """
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


def parse_polys(d, size):
    """Parse a Polys object: ALL polys, each with its raw index (no filtering).

    FPoly file record (RE 2026-11-12, fnd_14): compact NumVertices, FVector
    Base/Normal/TextureU/TextureV, N x FVector, dword Flags, objref Actor,
    objref Material, FName Item, compact iLink, compact iBrushPoly,
    dword LightMapScale, dword licensee int.
    """
    r = 1  # props: None terminator
    num = struct.unpack_from("<i", d, r)[0]
    r += 8  # Num + Max ints (UPolys::Serialize writes two dwords)

    polys = []
    for i in range(num):
        vc, r = read_compact(d, r)
        base = struct.unpack_from("<3f", d, r)
        r += 12
        normal = struct.unpack_from("<3f", d, r)
        r += 12
        tu = struct.unpack_from("<3f", d, r)
        r += 12
        tv = struct.unpack_from("<3f", d, r)
        r += 12
        verts = []
        ok = True
        for _ in range(max(0, vc)):
            if r + 12 > len(d):
                ok = False
                break
            verts.append(struct.unpack_from("<3f", d, r))
            r += 12
        flags = struct.unpack_from("<I", d, r)[0]
        r += 4
        _, r = read_compact(d, r)   # +0xF4 Actor objref
        poly_mat, r = read_compact(d, r)   # +0xF8 the FPoly's OWN Material
        _, r = read_compact(d, r)   # +0xFC Item (FName)
        _, r = read_compact(d, r)   # +0x104 iLink
        _, r = read_compact(d, r)   # +0x108 iBrushPoly
        r += 8
        if not ok:
            continue
        polys.append({
            "i": i, "verts": verts, "normal": normal, "tu": tu, "tv": tv,
            "base": base, "flags": flags, "poly_mat": poly_mat,
        })
    return polys


def resolve_tex(pkg, ref, shaders):
    """Resolve an object ref to a staged [package, object] texture pair.

    With the authentic compact decode the surf/polys material refs hit
    Texture/Shader imports exactly (findings fnd_13/fnd_14)."""
    if not isinstance(ref, int) or ref == 0:
        return None
    if ref > 0:
        j = ref - 1
        if j >= pkg.export_count:
            return None
        cls = pkg.class_of_export(j)
        nm = pkg.name(pkg.exports[j][3])
        if cls in ("Texture",):
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


def write_gltf(path, name, prims, prim_idx_of):
    """Write the renderable polys as one prim per poly.

    prims = the polys to render (already filtered by flags), prim_idx_of maps
    a raw poly index to its glTF prim index."""
    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    mesh_prims = []
    for pi, prim in enumerate(prims):
        pts = prim["verts"]
        if len(pts) < 3:
            continue  # degenerate: the face stays in bsp.json (prim null)
        if "uv_axes" not in prim:
            continue  # no usable texture axes (no same-plane surf)
        ubase, U, V = prim["uv_axes"]
        pos = []
        uvs = []
        for v in pts:
            pos.extend([v[0] * SCALE, v[2] * SCALE, v[1] * SCALE])
            # L2 BSP texture mapping: u = dot(P - pBase, pTextureU) in TEXELS
            # (the surf's U/V vectors carry the UE editor texel scale,
            # |U| = 0.5..4). The FPoly's own TextureU/V are degenerate (U
            # parallel to V in every 20_18 brush). world.gd scales the UVs
            # by 1/texture size per material.
            u = sum((v[k] - ubase[k]) * U[k] for k in range(3))
            w = sum((v[k] - ubase[k]) * V[k] for k in range(3))
            uvs.extend([u, w])
        idx = []
        for k in range(1, len(pts) - 1):
            idx.extend([0, k + 1, k])
        if len(idx) < 3:
            continue
        pb = struct.pack(f"<{len(pos)}f", *pos)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(pb)})
        blob.extend(pb)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                          "count": len(pts), "type": "VEC3",
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
        materials.append({"name": f"m{prim['i']}", "pbrMetallicRoughness":
                          {"baseColorFactor": [0.4, 0.4, 0.4, 1.0]},
                          "doubleSided": True})
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 3,
                                          "TEXCOORD_0": len(accessors) - 2},
                           "indices": len(accessors) - 1, "material": pi, "mode": 4})
        prim_idx_of[prim["i"]] = len(mesh_prims) - 1
    if not mesh_prims:
        return False
    gltf = {
        "asset": {"version": "2.0", "generator": "l2godot bsp2"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": mesh_prims}],
        "materials": materials,
        "accessors": accessors, "bufferViews": buffer_views,
        "buffers": [{"uri": name + ".bin", "byteLength": len(blob)}],
    }
    json.dump(gltf, open(path + ".gltf", "w"))
    open(path + ".bin", "wb").write(bytes(blob))
    return True


def model_polys_ref(pkg, midx, loc, pivot, polys_parse):
    """The Brush->Model->Polys link. The L2 UModel::Serialize does NOT carry
    the stock-UE2 `Ar << Polys` at the head; the reference is a compact
    object index (export+1) inside the Model's binary blob (Model954 holds
    compact 2260 = Polys370+1). Blobs can contain several compact values
    that decode into Polys exports; the true one is picked by placing the
    geometry with origin = Location - PrePivot and requiring the brush
    Location to fall inside the resulting world bbox (+/-150)."""
    cls, sup, pk, nm, fl, size, off = pkg.exports[midx]
    d = pkg.data[off:off + size]
    cands = []
    p = 0
    while p < len(d):
        v, q = read_compact(d, p)
        cands.append((p, v))
        p = q if q > p else p + 1
    refs = []
    for p, v in cands:
        j = v - 1
        if 0 <= j < pkg.export_count and pkg.class_of_export(j) == "Polys":
            refs.append((p, j))
    if not refs:
        return None
    if len(refs) == 1:
        return refs[0][1]
    origin = [loc[k] - pivot[k] for k in range(3)]
    for p, j in reversed(refs):
        P = polys_parse.get(j)
        if not P:
            continue
        vs = [v for pr in P for v in pr["verts"]]
        wmn = [min(v[k] for v in vs) + origin[k] for k in range(3)]
        wmx = [max(v[k] for v in vs) + origin[k] for k in range(3)]
        if all(wmn[k] - 150 <= loc[k] <= wmx[k] + 150 for k in range(3)):
            return j
    return refs[-1][1]


def find_level_model(pkg):
    """Find the level's BSP Model: scan every Level object's blob for compact
    object refs that resolve to a big Model export; take the biggest."""
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


def parse_model_surfs(pkg, midx):
    """Parse the level Model's Surfs array.

    Model file layout (RE 2026-11-12, fnd_14): props + FBox(25 B) + 4 dwords
    + Vectors TArray + Points TArray + Nodes TArray (FBspNode records) +
    Surfs TArray (FBspSurf records) + ... Each FBspSurf = {objref MATERIAL,
    dword PolyFlags, 5 compacts [pBase, pNormal, pTextureU, pTextureV,
    iBrushPoly], objref owner Brush, 16 B plane, float, int}."""
    off, size = pkg.exports[midx][6], pkg.exports[midx][5]
    d = pkg.data[off:off + size]

    def rc(p):
        return read_compact(d, p)

    p = 1 + 25 + 16  # props(None) + FBox(Min,Max,IsValid) + 4 dwords
    n, p = rc(p)
    vec = [struct.unpack_from("<3f", d, p + i * 12) for i in range(n)]
    p += n * 12
    n2, p = rc(p)
    pts = [struct.unpack_from("<3f", d, p + i * 12) for i in range(n2)]
    p += n2 * 12
    nnodes, p = rc(p)

    def node_skip(p):
        p += 16 + 8 + 1  # 4 dwords + 8 B + 1 byte
        for _ in range(7):  # compacts +0x18 +0x1c +0x20 +0x24 +0x28 +0x4c +0x50
            _, p = rc(p)
        p += 32 + 3 + 8 + 12  # 8 dwords + 3 bytes
        return p

    for _ in range(nnodes):
        p = node_skip(p)
    nsurf, p = rc(p)
    surfs = []
    for _ in range(nsurf):
        mat, p = rc(p)
        flags = struct.unpack_from("<I", d, p)[0]
        p += 4
        idx = []
        for _ in range(5):
            v, p = rc(p)
            idx.append(v)
        owner, p = rc(p)
        p += 24
        axes = None
        if idx[0] < len(pts) and idx[2] < len(vec) and idx[3] < len(vec):
            axes = (pts[idx[0]], vec[idx[2]], vec[idx[3]])
        pnrm = vec[idx[1]] if idx[1] < len(vec) else None
        surfs.append({"mat": mat, "flags": flags, "poly": idx[4], "owner": owner,
                      "axes": axes, "pnrm": pnrm})
    return {"surfs": surfs, "vec": vec, "pts": pts, "n_nodes": nnodes}


def main():
    map_path, asset_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    pkg = Package(map_path)
    shaders = json.load(open(os.path.join(asset_dir, "shader_diffuse.json")))

    # 0) the level Model + its surfs (the texture source)
    midx = find_level_model(pkg)
    model = parse_model_surfs(pkg, midx) if midx is not None else {"surfs": []}
    if midx is None:
        print("WARNING: no level Model found — no textures")
    surfs_by_owner = {}
    for s in model["surfs"]:
        surfs_by_owner.setdefault(s["owner"], []).append(s)
    all_surfs = [s for s in model["surfs"] if s.get("axes")]
    print(f"level model: export {midx}, {len(model['surfs'])} surfs, "
          f"{len(model['vec'])} vecs, {len(model['pts'])} pts, "
          f"{model.get('n_nodes', '?')} nodes")

    # 1) parse every Polys object (local-space polygons, ALL of them)
    polys_objs = {}
    polys_parse = {}
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) != "Polys":
            continue
        cls, sup, pk, nm, fl, size, off = pkg.exports[i]
        name = pkg.name(nm)
        try:
            parsed = parse_polys(pkg.data[off:off + size], size)
            polys_objs[name] = parsed
            polys_parse[i] = parsed
        except Exception as e:
            print(f"polys {name}: {e}")

    # 2) brushes: Location (- PrePivot) + Polys via the compact ref inside
    # the Model blob; faces from the level surfs (owner brush + iBrushPoly)
    brushes = []
    for i in range(pkg.export_count):
        if pkg.class_of_export(i) != "Brush":
            continue
        cls, sup, pk, nm, fl, size, off = pkg.exports[i]
        d = pkg.data[off:off + size]
        try:
            state, props, end = read_object(d, pkg, bool(fl & 0x02000000))
        except Exception:
            continue
        bref = props.get("Brush")
        loc = props.get("Location", (0, 0, 0))
        pivot = props.get("PrePivot", (0, 0, 0))
        if not isinstance(bref, int) or bref <= 0:
            continue
        j = model_polys_ref(pkg, bref - 1, loc, pivot, polys_parse)
        if j is None:
            continue
        pname = pkg.name(pkg.exports[j][3])
        if pname not in polys_objs:
            continue
        origin = [loc[k] - pivot[k] for k in range(3)]
        # per-face textures: surf(owner == this brush, iBrushPoly == poly idx)
        # (the surf owner ref = the Brush ACTOR's export index + 1, NOT the
        # Brush property which points to the brush's Model)
        surf_tex = {}
        surf_flags = {}
        surf_axes = {}
        for s in surfs_by_owner.get(i + 1, []):
            if s["poly"] not in surf_tex:
                surf_tex[s["poly"]] = s["mat"]
                surf_flags[s["poly"]] = s["flags"]
                surf_axes[s["poly"]] = s["axes"]
        faces = []
        for pr in polys_objs[pname]:
            k = pr["i"]
            # texture priority: the level surf's material, else the FPoly's
            # own authored material (the CSG may have dropped the surf but
            # the poly still knows its texture)
            tex_ref = surf_tex.get(k, None)
            if tex_ref is None or tex_ref == 0:
                tex_ref = pr.get("poly_mat")
            # texture axes: the surf's pBase/pTextureU/pTextureV — the FPoly's
            # own TextureU/V are degenerate (U parallel to V). For the
            # CSG-merged faces (no own surf) borrow the axes of a same-plane
            # surf of this brush (the normal match).
            axes = surf_axes.get(k)
            if axes is None:
                # the CSG-merged faces have no own surf: borrow the axes of a
                # same-plane surf — first among this brush's surfs, then
                # globally (the plane = the normal + the point distance)
                nrm = pr["normal"]
                v0 = pr["verts"][0]
                df = sum(v0[k] * nrm[k] for k in range(3))
                for s in surfs_by_owner.get(i + 1, []):
                    sv = s.get("pnrm")
                    if sv and abs(sv[0] * nrm[0] + sv[1] * nrm[1] + sv[2] * nrm[2]) > 0.99:
                        axes = s.get("axes")
                        if axes is not None:
                            break
                if axes is None:
                    for s in all_surfs:
                        sv = s.get("pnrm")
                        if not sv or abs(sv[0] * nrm[0] + sv[1] * nrm[1] + sv[2] * nrm[2]) < 0.99:
                            continue
                        sb = s.get("axes")
                        if not sb:
                            continue
                        ds = sum(sb[0][k] * sv[k] for k in range(3))
                        if abs(ds - df) < 20.0:
                            axes = sb
                            break
            faces.append({
                "i": k,
                "flags": surf_flags.get(k, pr["flags"]),
                "tex": resolve_tex(pkg, tex_ref, shaders),
            })
            if axes is not None:
                pr["uv_axes"] = axes
        brushes.append({"polys": pname, "location": origin, "faces": faces})

    # 3) export glTF per Polys: renderable faces only. A face renders iff it
    # has a surf texture, is not a marker (AntiPortal/ZonePortal) and carries
    # none of: invisible 0x1, fake backdrop 0x80, old-portal 0x4000000.
    # NOT 0x400000 — ordinary wall/street faces carry it and must render.
    # The texture requirement also drops the CSG-dropped coincident faces
    # (no surf -> hidden under the neighboring textured face) and the
    # zone/sky boxes (all their faces are tex-less markers).
    def face_renderable(pr, tex):
        if tex is None:
            return False
        if pr["flags"] & (0x4000000 | 0x1 | 0x80):
            return False
        if tex[1] in ("AntiPortal", "ZonePortal"):
            return False
        return True

    os.makedirs(out_dir, exist_ok=True)
    exported = []
    tex_of_poly = {}
    for br in brushes:
        for f in br["faces"]:
            tex_of_poly[(br["polys"], f["i"])] = f["tex"]
    for pname in sorted(polys_objs.keys()):
        prims = [pr for pr in polys_objs[pname]
                 if face_renderable(pr, tex_of_poly.get((pname, pr["i"])))]
        # the zone/sky separator brushes: huge spanning boxes (7.4k-11k units)
        # whose textured faces would hang giant slabs over the valley. The
        # biggest legitimate brush spans 4184 units (Polys17, the east
        # ruins) — 5000 splits them cleanly.
        if prims:
            xs = [v[0] for pr in polys_objs[pname] for v in pr["verts"]]
            ys = [v[1] for pr in polys_objs[pname] for v in pr["verts"]]
            if (max(xs) - min(xs)) > 5000 or (max(ys) - min(ys)) > 5000:
                prims = []
        prim_idx_of = {}
        path = os.path.join(out_dir, f"BSP_{pname}")
        if not write_gltf(path, f"BSP_{pname}", prims, prim_idx_of):
            continue
        exported.append(pname)
        for br in brushes:
            if br["polys"] == pname:
                for f in br["faces"]:
                    f["prim"] = prim_idx_of.get(f["i"])
    # faces of unexported polys: prim stays null

    # 4) coverage raster (unchanged semantics: HIGHEST walkable brush height)
    cover_z = {}
    for b in brushes:
        prims = polys_objs.get(b["polys"])
        if not prims:
            continue
        loc = b["location"]
        for pr in prims:
            pts3 = [(loc[0] + v[0], loc[1] + v[1], loc[2] + v[2]) for v in pr["verts"]]
            if len(pts3) < 3:
                continue
            xs = [p[0] for p in pts3]
            ys = [p[1] for p in pts3]
            zs = [p[2] for p in pts3]
            if max(zs) < -12000.0 or min(zs) > 12000.0:
                continue
            c_lo = max(0, int(min(xs) // CELL))
            c_hi = min(255, int(max(xs) // CELL))
            r_lo = max(0, int(min(ys) // CELL))
            r_hi = min(255, int(max(ys) // CELL))
            if c_lo > c_hi or r_lo > r_hi:
                continue
            z0, x0, y0 = pts3[0]
            e1 = (pts3[1][0] - pts3[0][0], pts3[1][1] - pts3[0][1], pts3[1][2] - pts3[0][2])
            e2 = (pts3[2][0] - pts3[0][0], pts3[2][1] - pts3[0][1], pts3[2][2] - pts3[0][2])
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]
            norm = abs(nx) + abs(ny) + abs(nz)
            if norm < 1e-9 or abs(nz) / norm < 0.05:
                continue
            inv_nz = 1.0 / nz
            for cc in range(c_lo, c_hi + 1):
                for rr in range(r_lo, r_hi + 1):
                    px = (cc + 0.5) * CELL
                    py = (rr + 0.5) * CELL
                    d1 = (px - pts3[1][0]) * (pts3[0][1] - pts3[1][1]) - (pts3[0][0] - pts3[1][0]) * (py - pts3[1][1])
                    d2 = (px - pts3[2][0]) * (pts3[1][1] - pts3[2][1]) - (pts3[1][0] - pts3[2][0]) * (py - pts3[2][1])
                    d3 = (px - pts3[0][0]) * (pts3[2][1] - pts3[0][1]) - (pts3[2][0] - pts3[0][0]) * (py - pts3[0][1])
                    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                    if not (neg and pos):
                        continue
                    z_game = z0 - (nx * (px - x0) + ny * (py - y0)) * inv_nz
                    if z_game < -12000.0 or z_game > 8000.0:
                        continue
                    z_val = z_game * SCALE
                    prev = cover_z.get((rr, cc))
                    if prev is None or z_val > prev:
                        cover_z[(rr, cc)] = z_val

    # stats
    with_tex = sum(1 for b in brushes for f in b["faces"] if f["tex"])
    total_faces = sum(len(b["faces"]) for b in brushes)
    json.dump({
        "schema": 2,
        "brushes": brushes,
        "cover_z": [[r, c, round(z, 2)] for (r, c), z in sorted(cover_z.items())],
    }, open(os.path.join(asset_dir, "bsp.json"), "w"), indent=1)
    print(f"polys objects: {len(polys_objs)}, exported glTF: {len(exported)}, "
          f"brushes: {len(brushes)}, faces: {total_faces} "
          f"(textured {with_tex}), cover cells: {len(cover_z)}")


if __name__ == "__main__":
    main()
