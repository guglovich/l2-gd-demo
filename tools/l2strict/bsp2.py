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
import numpy as np  # noqa: E402  (the displacement flat-copy fallback)
import disp  # noqa: E402  (the height-map displacement helper)

# displacement grid: texel steps per texture family + the per-face cap
DISP_STEP_TEXELS = {
    "DE_V_floor01": 8.0, "DE_V_floor02": 8.0, "oren_sylen_001_1": 8.0,
    "DE_V_m12": 16.0, "O_dark_01": 16.0,
}
DISP_MAX_POINTS = 8000

SCALE = 0.01
CELL = 128.0

# The Shillien Temple region (temple_native REGION): every Brush actor whose
# origin falls inside is a ZONE VOLUME — never rendered (DEVLOG-76).
TEMPLE_REGION = (25400, 31500, 8800, 17200)


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


def write_gltf(path, name, prims, prim_idx_of, tex_of=None, texroot=None):
    """Write the renderable polys as one prim per poly.

    prims = the polys to render (already filtered by flags), prim_idx_of maps
    a raw poly index to its glTF prim index. With tex_of/texroot an
    additional displaced mesh (<name>_D.gltf) is written from the texture
    height maps — REAL polygon relief (disp.py); prim i stays aligned with
    the flat mesh (non-displaceable prims carry a flat copy)."""
    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    mesh_prims = []
    ditems = []  # displaced-prim bookkeeping, aligned with mesh_prims
    if tex_of is not None and prims:
        allv = np.array([[v[0] * SCALE, v[2] * SCALE, v[1] * SCALE]
                         for pr in prims for v in pr["verts"]])
        bc = allv.mean(axis=0)  # brush center for the outward hint
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
        # One-sided BSP (the client rule, DEVLOG-82 rev2 / DEVLOG-153):
        # the emitted FRONT face must match the authored poly normal.
        # The Godot axes (x,z,y) mirror UE space, so the reversed fan
        # [0,k+1,k] fronts +normal exactly when Newell(UE)·normal > 0
        # (verified on Polys377: all 10 polys positive). Guard anyway.
        nrm = prim["normal"]
        nx = ny = nz = 0.0
        for k in range(len(pts)):
            a = pts[k]
            b = pts[(k + 1) % len(pts)]
            nx += (a[1] - b[1]) * (a[2] + b[2])
            ny += (a[2] - b[2]) * (a[0] + b[0])
            nz += (a[0] - b[0]) * (a[1] + b[1])
        keep = (nx * nrm[0] + ny * nrm[1] + nz * nrm[2]) > 0
        idx = []
        for k in range(1, len(pts) - 1):
            idx.extend([0, k + 1, k] if keep else [0, k, k + 1])
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
        # PF_TwoSided = 0x100 (Cruma Bsp.BspPolygonFlags): the client
        # culls backfaces on every other face — the plaza lattice plate's
        # floor01 UNDERSIDE (Polys377 poly9, normal down) must NOT plug
        # the Iron_net holes when seen from above (DEVLOG-153).
        materials.append({"name": f"m{prim['i']}", "pbrMetallicRoughness":
                          {"baseColorFactor": [0.4, 0.4, 0.4, 1.0]},
                          "doubleSided": prim.get("two_sided",
                                                 bool(prim["flags"] & 0x100))})
        # displaced-prim bookkeeping (REAL polygon relief, disp.py): same
        # prim order as the flat mesh. Heights are sampled from the texture
        # tile at the CANONICAL world-aligned UVs, so adjacent displaced
        # faces of one texture get identical heights at coincident points —
        # the geometry welds flush across the joints.
        if tex_of is not None and texroot is not None:
            gpos = [[v[0] * SCALE, v[2] * SCALE, v[1] * SCALE] for v in pts]
            guv = [[u, w] for u, w in
                   [(sum((v[k] - ubase[k]) * U[k] for k in range(3)),
                     sum((v[k] - ubase[k]) * V[k] for k in range(3))) for v in pts]]
            # outward hint: face centroid minus the brush bbox center (the
            # BSP winding is unreliable for the displacement sign)
            fc = np.mean(np.array(gpos), axis=0)
            outward = tuple(fc - bc)
            tex = tex_of.get(prim["i"])
            ditem = None
            if tex:
                h, pom = disp.height_field(texroot, tex[0], tex[1])
                if h is not None and pom > 0.02:
                    d = disp.displace_poly(
                        gpos, guv, h, pom,
                        max_points=DISP_MAX_POINTS,
                        step0=DISP_STEP_TEXELS.get(tex[1], 8.0),
                        outward=outward)
                    if d:
                        ditem = {"pos": d[0], "uv": d[1], "nrm": d[2], "idx": d[3]}
            if ditem is None:
                # flat copy keeps the prim aligned with the flat mesh
                a = np.array(gpos, dtype=np.float64)
                nv = np.cross(a[1] - a[0], a[2] - a[0])
                ln = np.linalg.norm(nv)
                nrm = nv / ln if ln > 1e-9 else np.array([0.0, 1.0, 0.0])
                nrms = np.tile(nrm, (len(gpos), 1))
                fidx = []
                for k in range(1, len(gpos) - 1):
                    fidx.extend([0, k + 1, k])
                ditem = {"pos": a, "uv": np.array(guv), "nrm": nrms,
                         "idx": np.asarray(fidx, dtype=np.int64)}
            ditems.append(ditem)
        # material index = the emitted-prim index, NOT the loop pi: degenerate
        # prims above `continue` without emitting, so pi drifts past the
        # materials array ("Index material = N out of bounds" import failure).
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 3,
                                          "TEXCOORD_0": len(accessors) - 2},
                           "indices": len(accessors) - 1,
                           "material": len(mesh_prims), "mode": 4})
        prim_idx_of[prim["i"]] = len(mesh_prims) - 1
    if not mesh_prims:
        return False
    # the displaced render mesh (prim-aligned); failure is non-fatal — the
    # flat mesh stays the render+collision fallback
    if tex_of is not None and texroot is not None and ditems:
        try:
            disp.write_displaced_gltf(path, name, ditems)
        except Exception as e:
            print(f"  displacement failed for {name}: {e}")
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


def _brush_overlaps_sub(br, polys_objs, sub_boxes):
    P = polys_objs.get(br["polys"])
    if not P or not sub_boxes:
        return False
    loc = br["location"]
    vs = [v for pr in P for v in pr["verts"]]
    xs = [v[0] + loc[0] for v in vs]
    ys = [v[1] + loc[1] for v in vs]
    zs = [v[2] + loc[2] for v in vs]
    bx = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    for x1, x2, y1, y2, z1, z2 in sub_boxes:
        if bx[0] <= x2 and bx[1] >= x1 and bx[2] <= y2 and \
                bx[3] >= y1 and bx[4] <= z2 and bx[5] >= z1:
            return True
    return False


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
        # DEVLOG-76: the Shillien Temple Brush actors are ZONE VOLUMES
        # (sound/light markers — Polys17 the hall box, Polys23/28 the
        # passage slabs, Polys51 the apse volume, Polys71/59 the stair
        # corridors, Polys83/79 the march duplicates, Polys91..111 the
        # apse caps): the level BSP carries zero temple geometry and the
        # client renders the interior from static meshes ALONE (deco08 =
        # hall floor+walls, ent_stair/ent_stair02 = the west marches at
        # the same heights, side_stair = the corridor ramps, deco03 = the
        # apse floor). Every brush face here is a zone-volume face — the
        # source of the alien walls, the gray in002 squares and the
        # duplicate ramps. Modern-port rule: never render zone separators.
        # The region is the temple_native REGION; the village road brushes
        # lie outside it (the golden baseline gates this).
        if (TEMPLE_REGION[0] <= origin[0] <= TEMPLE_REGION[1]
                and TEMPLE_REGION[2] <= origin[1] <= TEMPLE_REGION[3]):
            continue
        # CsgOper: 1 = CSG_Add (solid), 2 = CSG_Subtract (the carved AIR —
        # the engine renders the subtraction result, never the brush itself)
        csg = props.get("CsgOper")
        csg = int(csg) if isinstance(csg, int) else 1
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
            # the SURF PolyFlags are authoritative (the client renders the
            # node's surf, not the raw FPoly) — PF_TwoSided 0x100
            pr["two_sided"] = bool(surf_flags.get(k, pr["flags"]) & 0x100)
        brushes.append({"polys": pname, "location": origin, "faces": faces,
                        "csg": csg})

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
    # The subtractive brushes (CsgOper=2) = the carved AIR per the map data;
    # per the modern-port rule we do NOT emulate the legacy CSG carving —
    # they are simply not rendered. The ADD brushes that overlap a small
    # subtract volume = the legacy carved-context housings (the masonry
    # boxes around the carved passages) — they are not built either: the
    # passage stays open and the surrounding native meshes (the inlet, the
    # terrain, the level BSP) provide the walls.
    sub_boxes = []
    for br in brushes:
        if br.get("csg") != 2:
            continue
        P = polys_objs.get(br["polys"])
        if not P:
            continue
        loc = br["location"]
        vs = [v for pr in P for v in pr["verts"]]
        xs = [v[0] + loc[0] for v in vs]
        ys = [v[1] + loc[1] for v in vs]
        zs = [v[2] + loc[2] for v in vs]
        if (max(xs) - min(xs)) > 1500 or (max(ys) - min(ys)) > 1500:
            continue  # the giant zone/sky separators
        sub_boxes.append((min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))

    def overlaps_sub(bxs):
        for x1, x2, y1, y2, z1, z2 in sub_boxes:
            if bxs[0] <= x2 and bxs[1] >= x1 and bxs[2] <= y2 and \
                    bxs[3] >= y1 and bxs[4] <= z2 and bxs[5] >= z1:
                return True
        return False

    brushes = [br for br in brushes if br.get("csg") == 2 or not
               _brush_overlaps_sub(br, polys_objs, sub_boxes)]

    exported = []
    tex_of_poly = {}
    csg_of = {}
    for br in brushes:
        csg_of[br["polys"]] = br.get("csg", 1)
        for f in br["faces"]:
            tex_of_poly[(br["polys"], f["i"])] = f["tex"]

    # CANONICAL TEXTURE PROJECTION for the chaotic stone textures: all faces
    # of one texture share ONE (U,V) projection through the global origin.
    # The per-surf texture pans made coplanar faces tile with phase
    # mismatches — the visible "стык" on the road plates — and produced the
    # -30000..-80000-texel UV offsets. Aligned art (carpets, the ornament
    # medallions) keeps its own axes.
    #
    # 2026-11-14 (the user: "one continuous texture over the whole road"):
    # the phase continuity was not enough — the road plates carried
    # DIFFERENT texel scales of the same texture (floor01 at ~195 texels/m
    # dominant but also 97.5 and 53.7; floor02 390 vs 97.5; sylen 200 vs
    # 250), and the pattern density jumped at the plate boundaries. The
    # family is chosen per (texture, ORIENTATION CLASS): faces are bucketed
    # by the quantized face normal, each orientation class gets its own
    # DOMINANT (U,V). A single per-texture family let a wall family win
    # (the levelbsp floor01: 5 wall faces of 116) and left the horizontal
    # slabs at their own half-scale — the стык on the main road. Forcing
    # axes not in the face plane was the "мусор" regression (2026-11-13).
    CANON_UV_TEXS = {"DE_V_floor01", "O_dark_01", "DE_V_m12",
                     "oren_sylen_001_1", "DE_V_floor02"}
    prim_of = {}
    for pname2, prims2 in polys_objs.items():
        for pr2 in prims2:
            prim_of[(pname2, pr2["i"])] = pr2

    def _face_normal(verts):
        """Newell's method — robust for polygon fans where the first three
        vertices can be nearly collinear (a cross of v0..v2 is garbage
        there and poisoned the orientation buckets)"""
        if not verts or len(verts) < 3:
            return None
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

    counts = {}
    axes_of = {}
    for (pname2, i2), t2 in tex_of_poly.items():
        if not t2 or t2[1] not in CANON_UV_TEXS:
            continue
        pr2 = prim_of.get((pname2, i2))
        ax = pr2.get("uv_axes") if pr2 else None
        if not ax or not pr2.get("verts") or len(pr2["verts"]) < 3:
            continue
        U2, V2 = ax[1], ax[2]
        if sum(x * x for x in U2) < 1e-6:
            continue
        N2 = _face_normal(pr2["verts"])
        if N2 is None or not _in_plane(U2, V2, N2):
            continue
        nk = tuple(round(x, 1) for x in N2)
        ck = (t2[0], t2[1], nk, tuple(round(x, 3) for x in U2),
              tuple(round(x, 3) for x in V2))
        counts[ck] = counts.get(ck, 0) + 1
        axes_of.setdefault(ck, (U2, V2))
    # dominant (U,V) per (texture, orientation bucket)
    best = {}
    for (pkg2, tex2, nk, du, dv), c in counts.items():
        bk = (pkg2, tex2, nk)
        if c > best.get(bk, (0, None))[0]:
            best[bk] = (c, (du, dv))
    for (pname2, i2), t2 in tex_of_poly.items():
        if not t2 or t2[1] not in CANON_UV_TEXS:
            continue
        pr2 = prim_of.get((pname2, i2))
        if pr2 is None or "uv_axes" not in pr2 or not pr2.get("verts") \
                or len(pr2["verts"]) < 3:
            continue
        N2 = _face_normal(pr2["verts"])
        if N2 is None:
            continue
        nk = tuple(round(x, 1) for x in N2)
        bk = (t2[0], t2[1], nk)
        if bk in best:
            du, dv = best[bk][1]
            U2, V2 = axes_of[(bk[0], bk[1], nk, du, dv)]
            if _in_plane(U2, V2, N2):
                pr2["uv_axes"] = ((0.0, 0.0, 0.0), U2, V2)

    for pname in sorted(polys_objs.keys()):
        prims = []
        if csg_of.get(pname, 1) != 2:
            for pr in polys_objs[pname]:
                if not face_renderable(pr, tex_of_poly.get((pname, pr["i"]))):
                    continue
                prims.append(pr)
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
        # EXPERIMENT switch (the 3D-geometry stage, one small step at a time):
        # L2_DISP_BRUSH=<polys>[,<polys>…] emits <name>_D.gltf — the
        # height-displaced render mesh — ONLY for the named brushes. Normal
        # builds pass tex_of=None and write nothing extra.
        disp_names = [s.strip() for s in
                      os.environ.get("L2_DISP_BRUSH", "").split(",") if s.strip()]
        tex_of = None
        if pname in disp_names:
            tex_of = {i: t for (pn, i), t in tex_of_poly.items() if pn == pname}
        if not write_gltf(path, f"BSP_{pname}", prims, prim_idx_of,
                          tex_of=tex_of,
                          texroot=os.path.join(out_dir, "..", "textures")
                          if tex_of is not None else None):
            continue
        exported.append(pname)
        for br in brushes:
            if br["polys"] == pname:
                for f in br["faces"]:
                    f["prim"] = prim_idx_of.get(f["i"])
    # faces of unexported polys: prim stays null
    # Self-clean: a polys that renders no prims this run must NOT leave its
    # stale glTF in out_dir (old-format files kept failing Godot import with
    # "Index material out of bounds"). Prune anything not written above.
    for fn in os.listdir(out_dir):
        base, ext = os.path.splitext(fn)
        if ext not in (".gltf", ".bin") or not base.startswith("BSP_"):
            continue
        if base.endswith("_D"):  # the displaced variant shares the fate
            base = base[:-2]
        if base[4:] not in exported:  # file base = "BSP_" + polys name
            os.remove(os.path.join(out_dir, fn))

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
