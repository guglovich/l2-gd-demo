#!/usr/bin/env python3
"""L2 StaticMesh -> glTF exporter (independent of UModel).

Layout was reverse-engineered from engine.dll (UStaticMesh::Serialize,
UPrimitive::Serialize, 0x103108c5 / 0x10311293) and verified against
Oren_DEV_S.usx / O_DE_MT_Btm (452 verts / 422 faces):

  after the property list:
    FBox    BoundingBox   (24 B: min.xyz max.xyz, UE (X,Y,Z))
    FSphere BoundingSphere(16 B: center.xyz, radius)
    FStaticMeshVertexStream: compact count, count*24 B (Pos 3f32 + Normal
      3f32, unit length), int Revision
    FRawColorStream (Colors) / FRawColorStream (Alpha): compact count,
      count*4 B, int Revision
    UVStreams: compact K, per stream: compact count, count*8 B (2 f32),
      int, int
    IndexStream1/2: compact count, count*u16, int Revision
  then L2 licensee data (TLazyArray Faces / kDOP ...) — not needed here.

glTF axis mapping (same as the UModel pipeline): (x, z, -y) m = UE/100.
"""
import json
import math
import os
import struct


class Reader:
    def __init__(self, data: bytes, pos: int = 0):
        self.d = data
        self.p = pos

    def u8(self) -> int:
        b = self.d[self.p]
        self.p += 1
        return b

    def i32(self) -> int:
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self) -> float:
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def compact(self) -> int:
        """UE compact index (1-3 bytes, little-endian, sign via 0x80)."""
        b = self.u8()
        negative = bool(b & 0x80)
        more = bool(b & 0x40)
        value = b & 0x3F
        shift = 6
        while more:
            b = self.u8()
            more = bool(b & 0x80)
            value |= (b & 0x7F) << shift
            shift += 7
        return -(value + 1) if negative else value

    def raw(self, n: int) -> bytes:
        r = self.d[self.p:self.p + n]
        self.p += n
        return r


def _valid_vertex(rec: bytes) -> bool:
    x, y, z, nx, ny, nz = struct.unpack("<6f", rec)
    if not all(abs(v) < 1.2e5 for v in (x, y, z)):
        return False
    if not all(abs(v) <= 1.001 for v in (nx, ny, nz)):
        return False
    return abs(nx * nx + ny * ny + nz * nz - 1.0) < 0.02


def _find_sections(data: bytes, bulk_start: int, bulk_end: int,
                   want_faces: int) -> list:
    """Locate the FStaticMeshSection table: compact count followed by
    count x 14-B entries (i32 f4=0; u16 FirstIndex; FirstVertex;
    LastVertex; fE; NumFaces) — the standard UE2 layout. Oracle: the
    FirstIndex sequence is non-decreasing and consecutive sections chain
    (FI + NF*3 = next FI). Verified on Oren_DEV_S (Bridge: 18 sections,
    sum NF = 924 = the whole index pool)."""
    best = None
    for off in range(bulk_start, bulk_end - 16):
        rr = Reader(data, off)
        try:
            cnt = rr.compact()
        except IndexError:
            continue
        if cnt <= 0 or cnt > 64:
            continue
        ok = True
        secs = []
        prev_fi = -1
        for _ in range(cnt):
            if rr.p + 14 > bulk_end:
                ok = False
                break
            f4, fi, fv, lv, fe, nf = struct.unpack_from("<IHHHHH", data, rr.p)
            rr.p += 14
            if f4 != 0 or fi < prev_fi:
                ok = False
                break
            if nf == 0:
                # an empty section is legal (UModel skips it in the output)
                secs.append((fi, fv, lv, fe, nf))
                continue
            if fv > lv or lv >= 30000 or fi + nf * 3 > 30000:
                ok = False
                break
            prev_fi = fi
            secs.append((fi, fv, lv, fe, nf))
        if not ok or not secs:
            continue
        covered = sum(s[4] for s in secs)
        if covered == want_faces:
            return secs
        if best is None or covered > sum(s[4] for s in best):
            best = secs
    return best or []


def parse_static_mesh(data: bytes, start: int, size: int,
                      hint_verts: int = 0,
                      hint_plan: list | None = None,
                      name: str = "") -> dict:
    """Parse one L2 StaticMesh binary bulk (props already consumed).

    Anchor-based (format-proof): the vertex stream is located by its
    compact count (== the hint from the staged glTF) followed by count
    x 24 B records (pos + normal, the L2 normals have length 512);
    the color/alpha/UV streams share the same element count; the index
    streams are u16 pools; the sections are 14-B tables whose NumFaces
    sum x 3 == the index count.

    ``hint_plan`` = [(index_count, material_index), ...] from the staged
    UModel glTF. When the on-file section table resists the oracle (the
    Pir01 class: sections serialize behind the L2 variable header and the
    kDOP object — RE pending), the plan slices the real render index pool
    contiguously and carries per-section material indices. UModel's
    per-section index counts sum exactly to the real pool length, so the
    slicing is exact; the index VALUES stay from the file (UModel's own
    indices for this class are fabricated).
    """
    d = data
    end = start + size

    def compact(p):
        b = d[p]
        more = b & 0x40
        neg = b & 0x80
        v = b & 0x3F
        sh = 6
        p += 1
        while more:
            b = d[p]
            more = b & 0x80
            v |= (b & 0x7F) << sh
            sh += 7
            p += 1
        return (-(v + 1) if neg else v), p

    def valid_rec(p, stride=24):
        x, y, z, nx, ny, nz = struct.unpack_from("<6f", d, p)
        if not all(abs(t) < 1.2e5 for t in (x, y, z)):
            return 0
        ln2 = nx * nx + ny * ny + nz * nz
        # L2 normals: unit length OR the engine's 512 scale
        if not (0.9 < ln2 < 1.1 or 250000 < ln2 < 275000):
            return 0
        if stride == 32:
            u, v = struct.unpack_from("<2f", d, p + 24)
            if abs(u) > 16 or abs(v) > 16:
                return 0
        return 1

    # --- locate the vertex stream as the LONGEST valid 24-B record run.
    # The stream offset is not aligned to anything (it follows the compact
    # count + the L2 header fields), so the scan walks EVERY byte offset.
    # No hint needed: the run length IS the vertex count (this replaced the
    # hint-compact-pattern anchor whose false positives/negatives produced
    # the wrong 24-vert "slabs" and the phantom "packed-vertex" class).
    # Guard: the stream = [compact count == the run length][records] — a
    # candidate run must be preceded by its own compact count (the kDOP
    # float blocks can form accidental runs but never with the count).
    runs = []  # the maximal (length, offset) pairs, longest-first later
    # vectorized scan (numpy): the records are f32-aligned, so only 4 byte
    # phases exist; per phase the records form a strided 6-float grid.
    import numpy as _np
    for phase in range(24):  # the record stride = 24 B: 24 byte phases
        tail = d[start + phase:end]
        tail = tail[:len(tail) - (len(tail) % 4)]
        buf = _np.frombuffer(tail, dtype='<f4')
        m = buf.size // 6
        if m < 8:
            continue
        rec = buf[:m * 6].reshape(m, 6).astype(_np.float32)
        pos_ok = (_np.abs(rec) < 1.2e5).all(axis=1)
        ln2 = rec[:, 3] ** 2 + rec[:, 4] ** 2 + rec[:, 5] ** 2
        nrm_ok = ((ln2 > 0.9) & (ln2 < 1.1)) | ((ln2 > 250000) & (ln2 < 275000))
        good = pos_ok & nrm_ok
        if not good.any():
            continue
        padded = _np.concatenate(([False], good, [False]))
        diffs = _np.diff(padded.astype(_np.int8))
        starts = _np.flatnonzero(diffs == 1)
        stops = _np.flatnonzero(diffs == -1)
        for s0, s1 in zip(starts, stops):
            if s1 - s0 >= 8:
                runs.append((int(s1 - s0), start + phase + int(s0) * 24))
    vstart = None
    vcount = 0
    vstride = 24
    for length, off in sorted(runs, reverse=True):
        if length < 8:
            break
        # the compact count must end exactly at `off` and equal `length`
        ok = False
        for back in (1, 2, 3):
            q = off - back
            if q < start:
                break
            c, p2 = compact(q)
            if p2 == off and c == length:
                ok = True
                break
        if ok:
            vstart = off
            vcount = length
            break
    if vcount < 8:
        raise ValueError("no count-guarded 24-B vertex stream in the bulk")
    verts = []
    for i in range(vcount):
        p = vstart + i * vstride
        x, y, z, nx, ny, nz = struct.unpack_from("<6f", d, p)
        l = (nx * nx + ny * ny + nz * nz) ** 0.5
        if l > 2.0:
            nx, ny, nz = nx / l, ny / l, nz / l
        if vstride == 32:
            u, v = struct.unpack_from("<2f", d, p + 24)
            verts.append((x, y, z, nx, ny, nz, u, v))
        else:
            verts.append((x, y, z, nx, ny, nz))
    r = vstart + vcount * vstride

    # --- the color / alpha / UV streams share the element count. Each
    # stream = [compact count][payload][4-B tail], but 1-2 extra bytes may
    # sit before a count (the Bridge's UV stream carries a stray 0x01) —
    # retry the SAME width over a small byte window instead of skipping
    # to the next width (the old walk lost the UV stream entirely and
    # every staged mesh rendered with (0,0) UVs = flat untextured).
    uvs = []
    p = r + 4
    for width in (4, 4, 8):
        got = False
        for shift in range(0, 16):
            p0 = p + shift
            if p0 >= end:
                break
            c, p2 = compact(p0)
            if c != vcount:
                continue
            p = p2
            if width == 8:
                uvs = [struct.unpack_from("<2f", d, p + i * 8) for i in range(c)]
            p += c * width
            p += 4
            got = True
            break
        if not got:
            break

    # --- index streams: compact count + u16 pool with values < vcount
    indices = []
    p = r
    while p < end - 4:
        c, p2 = compact(p)
        if 8 <= c <= 4_000_000 and p2 + c * 2 + 4 <= end:
            pool = struct.unpack_from(f"<{c}H", d, p2)
            if max(pool) < vcount:
                indices.append(pool)
                p = p2 + c * 2 + 4
                continue
        p += 1
    render_idx = None
    for idx in indices:
        if idx and max(idx) < vcount:
            render_idx = idx
            break
    if render_idx is None:
        raise ValueError("no render index stream referencing the vertex pool")

    # --- sections: 14-B entries (f4 i32=0; FirstIndex, FirstVertex,
    # LastVertex, fE, NumFaces as u16). Empty sections (NumFaces=0) are
    # legal. Oracle: sum(NumFaces)*3 == the index count.
    sections = []
    idx_total = len(render_idx)
    best = None
    # The L2 section table sits BEFORE the bbox (the engine's
    # UPrimitive::Serialize emits it right after the props — UEViewer's
    # "Ar << Sections; Ar << BoundingBox" order), so the scan starts in
    # the pre-bulk region.
    scan_begin = max(0, start - 4096)
    scan_end = min(vstart, start + 4096) - 16
    import os as _os
    _dbg = _os.environ.get("L2_SECTION_DEBUG") != ""
    for off in range(scan_begin, scan_end):
        cc, p2 = compact(off)
        if cc <= 0 or cc > 64:
            continue
        if _dbg and 30 <= off - start <= 60:
            print(f"SECDBG off=+{off-start} cc={cc}")
        ok = True
        secs = []
        prev_fi = -1
        for _ in range(cc):
            if p2 + 14 > end:
                ok = False
                if _dbg and 30 <= off - start <= 60:
                    print("SECDBG   over bulk end")
                break
            f4, fi, fv, lv, fe, nf = struct.unpack_from("<IHHHHH", d, p2)
            p2 += 14
            if f4 != 0 or fi < prev_fi or fi + nf * 3 > idx_total:
                ok = False
                if _dbg and 30 <= off - start <= 60:
                    print(f"SECDBG   fail1: f4={f4} fi={fi} nf={nf} idx_total={idx_total}")
                break
            if nf and (fv > lv or lv >= vcount):
                ok = False
                if _dbg and 30 <= off - start <= 60:
                    print(f"SECDBG   fail2: fv={fv} lv={lv} vcount={vcount}")
                break
            prev_fi = fi
            secs.append((fi, fv, lv, fe, nf))
        if not ok or not secs:
            continue
        covered = sum(s[4] for s in secs) * 3
        if _dbg and 30 <= off - start <= 60:
            print(f"SECDBG   table valid covered={covered} need={idx_total}")
        if covered == idx_total:
            sections = secs
            break
        if best is None or covered > sum(s[4] for s in best):
            best = secs
    if not sections:
        sections = best or []

    # --- the road-plate family: the verts form a FLAT strip (the quad
    # chain along the road); the packed face entries are undecoded, so
    # build the faces as the quad chain. This replaces the wrong
    # fabricated faces with the correct flat-plate surface.
    section_materials = []
    if name in _ROAD_PLATE_MESHES:
        strip = _flat_strip_faces(verts)
        if strip is not None:
            render_idx = strip
            idx_total = len(strip)
            sections = [(0, 0, vcount - 1, len(strip) // 3, len(strip) // 3)]

    # --- UModel-plan fallback: slice the render pool contiguously by the
    # staged glTF's per-primitive index counts (they sum to the pool
    # length); carry the per-section material indices for world.gd.
    covered = sum(s[4] for s in sections) * 3
    if covered < idx_total and hint_plan:
        plan_total = sum(c for c, _m in hint_plan)
        if plan_total == idx_total:
            off = 0
            fsecs = []
            fmats = []
            for cnt, mat in hint_plan:
                nf = cnt // 3
                if nf <= 0:
                    continue
                fsecs.append((off, 0, vcount - 1, nf, nf))
                fmats.append(int(mat))
                off += cnt
            if off == idx_total and fsecs:
                sections = fsecs
                section_materials = fmats

    return {
        "bbox_min": struct.unpack_from("<3f", d, start),
        "bbox_max": struct.unpack_from("<3f", d, start + 12),
        "sphere": struct.unpack_from("<4f", d, start + 24),
        "verts": verts,
        "uvs": uvs,
        "indices": render_idx,
        "sections": sections,
        "section_materials": section_materials,
        "vertex_revision": 0,
    }


def _flat_strip_faces(verts: list) -> list | None:
    """Faces for a FLAT vertex strip: the verts = the consecutive
    cross-section pairs (2 per section), all at (nearly) the same height.
    The road plates (Btm_Obj01/02/03) are exactly this: a quad chain
    along the road. The winding is normalized per quad so every face
    normal points +z (the plate's top). Returns the index list or None
    when the verts are not a flat strip (the height span > 10 cm or the
    odd count)."""
    if len(verts) < 8 or len(verts) % 2:
        return None
    zs = [v[2] for v in verts]
    if max(zs) - min(zs) > 10.0:
        return None
    indices = []
    sections = len(verts) // 2
    for k in range(sections - 1):
        a, b = 2 * k, 2 * k + 1          # the section k's pair
        c, dd = 2 * k + 2, 2 * k + 3     # the section k+1's pair
        # the quad (a, b, dd, c); normalize the winding by the normal z
        ax, ay = verts[a][0], verts[a][1]
        bx, by = verts[b][0], verts[b][1]
        dx, dy = verts[dd][0], verts[dd][1]
        cross_z = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax)
        if cross_z >= 0:
            indices.extend([a, b, dd, a, dd, c])
        else:
            indices.extend([a, dd, b, a, c, dd])
    return indices


def write_gltf(path: str, name: str, mesh: dict) -> None:
    """Write the parsed mesh as glTF (+bin) in Godot-ready axes/scale."""
    blob = bytearray()
    buffer_views = []
    accessors = []

    positions = []
    for x, y, z, *_ in mesh["verts"]:
        # UModel's glTF convention (verified in-game and byte-wise:
        # um vert0 = raw (x, z, y) / 100, DEVLOG final6): game Y goes to
        # glTF Z WITHOUT negation. The earlier -y mirrored every mesh in
        # game Y (improper transform with the raw winding order kept —
        # inside-out geometry vs the UModel-staged reference).
        positions.extend([x * 0.01, z * 0.01, y * 0.01])
    normals = []
    for *_, nx, ny, nz in mesh["verts"]:
        l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        normals.extend([nx / l, nz / l, ny / l])
    if mesh["uvs"]:
        # separate UV stream (the 24-B pos+normal vertex format):
        # mesh["uvs"] = one (u, v) tuple per vertex
        uv_flat = []
        for u, v in mesh["uvs"]:
            uv_flat.extend([u, 1.0 - v])
    elif len(mesh["verts"][0]) == 8:
        # inline UVs (the 32/36-B interleaved vertex format)
        uv_flat = []
        for v in mesh["verts"]:
            uv_flat.extend([v[6], 1.0 - v[7]])
    else:
        uv_flat = [0.0, 0.0] * len(mesh["verts"])

    def add_view(data: bytes) -> int:
        while len(blob) % 4:
            blob.append(0)
        buffer_views.append({
            "buffer": 0, "byteOffset": len(blob), "byteLength": len(data),
        })
        blob.extend(data)
        return len(buffer_views) - 1

    def add_acc(view: int, comp: int, count: int, kind: str,
                mn=None, mx=None) -> int:
        acc = {
            "bufferView": view, "componentType": comp,
            "count": count, "type": kind,
        }
        if mn is not None:
            acc["min"] = mn
            acc["max"] = mx
        accessors.append(acc)
        return len(accessors) - 1

    pb = struct.pack(f"<{len(positions)}f", *positions)
    pv = add_view(pb)
    pos_acc = add_acc(
        pv, 5126, len(mesh["verts"]), "VEC3",
        [min(positions[0::3]), min(positions[1::3]), min(positions[2::3])],
        [max(positions[0::3]), max(positions[1::3]), max(positions[2::3])],
    )
    nb = struct.pack(f"<{len(normals)}f", *normals)
    nv = add_view(nb)
    nrm_acc = add_acc(nv, 5126, len(mesh["verts"]), "VEC3")
    ub = struct.pack(f"<{len(uv_flat)}f", *uv_flat)
    uvv = add_view(ub)
    uv_acc = add_acc(uvv, 5126, len(mesh["verts"]), "VEC2")
    ib = struct.pack(f"<{len(mesh['indices'])}H", *mesh["indices"])
    iv = add_view(ib)
    idx_acc = add_acc(iv, 5123, len(mesh["indices"]), "SCALAR")

    # One primitive per section (world.gd maps textures per primitive via
    # asset_map's primitive_material_indices — read from these "material"
    # fields). section_materials carries the mesh's real material indices
    # (the UModel-plan fallback); without it the mapping is the identity.
    prims = []
    sec_mats = mesh.get("section_materials") or []
    secs = mesh.get("sections") or [(0, 0, len(mesh["verts"]) - 1, 0,
                                     len(mesh["indices"]) // 3)]
    used = 0
    for si, (fi, fv, lv, fe, nf) in enumerate(secs):
        sub = mesh["indices"][fi:fi + nf * 3]  # FirstIndex is in index units
        if not sub:
            continue
        used += len(sub) // 3
        sb = struct.pack(f"<{len(sub)}H", *sub)
        sv = add_view(sb)
        s_acc = add_acc(sv, 5123, len(sub), "SCALAR")
        mat = sec_mats[si] if si < len(sec_mats) else si
        prims.append({
            "attributes": {
                "POSITION": pos_acc,
                "NORMAL": nrm_acc,
                "TEXCOORD_0": uv_acc,
            },
            "indices": s_acc,
            "material": mat,
            "mode": 4,
        })
    if not prims or used * 3 < len(mesh["indices"]):
        # fallback: single primitive with everything
        prims = [{
            "attributes": {
                "POSITION": pos_acc,
                "NORMAL": nrm_acc,
                "TEXCOORD_0": uv_acc,
            },
            "indices": idx_acc,
            "material": 0,
            "mode": 4,
        }]

    n_mat = max([p["material"] for p in prims], default=0) + 1
    gltf = {
        "asset": {"version": "2.0", "generator": "l2strict staticmesh"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": prims}],
        "materials": [{
            "name": f"l2mat{i}",
            "pbrMetallicRoughness": {"baseColorFactor": [0.5, 0.5, 0.5, 1.0]},
            "doubleSided": True,
        } for i in range(n_mat)],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"uri": name + ".bin", "byteLength": len(blob)}],
    }
    with open(path + ".gltf", "w") as fp:
        json.dump(gltf, fp)
    with open(path + ".bin", "wb") as fp:
        fp.write(bytes(blob))


def _road_slab_mesh(data: bytes, bulk: int, hint_plan: list | None) -> dict:
    """The interim wide road slab for the strip family: the box from the
    file's exact bbox footprint (x) + the measured road width (10.5 m, the
    Bridge deck's z-span) + the measured road height (the top layer's
    raw z = +90..+102 => the world -44.06, the user's walking level).
    The exact outlines come from the packed decoder later; this slab
    restores the wide walkable road now."""
    mn = struct.unpack_from('<3f', data, bulk)
    mx = struct.unpack_from('<3f', data, bulk + 12)
    xlo, xhi = min(mn[0], mx[0]), max(mn[0], mx[0])
    ylo, yhi = -525.0, 525.0          # the road width = the deck's 10.5 m
    zlo, zhi = 90.0, 102.0            # the top = the raw +102 => -44.06 world
    cs = [(x, y, z) for x in (xlo, xhi) for y in (ylo, yhi) for z in (zlo, zhi)]
    quads = [
        (1, 3, 7, 5), (0, 4, 6, 2),
        (0, 1, 3, 2), (4, 6, 7, 5),
        (0, 1, 5, 4), (2, 6, 7, 3),
    ]
    indices = []
    for a, b, c, dd in quads:
        indices.extend([a, b, c, a, c, dd])
    # the u runs ACROSS the road (the width), the v ALONG it (the length):
    # the strip textures carry the ornamental band along the v axis, so
    # the band runs forward along the road (the reference orientation).
    # ONE texture repeat across the road width (10.5 m); the pattern
    # repeats along the length every 2.56 m as in the original.
    uvs = [((cy - ylo) / 1050.0, (cx - xlo) / 256.0) for cx, cy, cz in cs]
    mat = hint_plan[0][1] if hint_plan else 0
    return {
        "bbox_min": (xlo, ylo, zlo), "bbox_max": (xhi, yhi, zhi),
        "sphere": struct.unpack_from('<4f', data, bulk + 24),
        "verts": [(cx, cy, cz, 0.0, 0.0, 1.0) for cx, cy, cz in cs],
        "uvs": uvs,
        "indices": indices,
        "sections": [(0, 0, len(cs) - 1, len(indices) // 3,
                      len(indices) // 3)],
        "section_materials": [mat],
        "vertex_revision": 0,
    }


def _flat_plate_mesh(data: bytes, start: int, end: int,
                     hint_plan: list | None) -> dict | None:
    """Extract a flat road plate: a cluster of vertex triplets sharing a
    CONSTANT height. The L2 file vertex = (X, Z, Y) — the height is the
    SECOND column (the same order UModel's glTF mapping exposes; confirmed
    by the Btm_Obj01 plate: the column-1 values collapse to -102.87 while
    the column-0 spans 22 m and the column-2 spans 2.56 m). The road plates
    (Btm_Obj01/02/03) store their vertices as raw 12-B positions inside
    variable-length packed entries — invisible to fixed-stride scans.
    Returns the thin-plate mesh built from the cluster bounds, or None."""
    import numpy as _np
    span = end - start
    if span < 64:
        return None
    tail = data[start:end]
    tail = tail[:len(tail) - (len(tail) % 4)]
    buf = _np.frombuffer(tail, dtype='<f4')
    n3 = buf.size // 3
    if n3 < 16:
        return None
    tri = buf[:n3 * 3].reshape(n3, 3).astype(_np.float32)
    tri = tri[_np.isfinite(tri).all(axis=1)]
    if tri.shape[0] < 16:
        return None
    best = None
    zs = tri[:, 1]  # the height column
    for zc in _np.unique(zs):
        mask = _np.abs(zs - zc) < 2.0
        cnt = int(mask.sum())
        if cnt < 24:
            continue
        pts = tri[mask]
        xlo, xhi = float(pts[:, 0].min()), float(pts[:, 0].max())
        ylo, yhi = float(pts[:, 2].min()), float(pts[:, 2].max())
        if xhi - xlo < 400 or yhi - ylo < 150:
            continue
        if best is None or cnt > best[0]:
            best = (cnt, zc, xlo, xhi, ylo, yhi)
    if best is None:
        return None
    cnt, zc, xlo, xhi, ylo, yhi = best
    # the plate = the flat slab at raw z = zc; the thickness = 12 cm down
    zt, zb = float(zc), float(zc) - 12.0
    cs = [(x, y, z) for x in (xlo, xhi) for y in (ylo, yhi) for z in (zt, zb)]
    quads = [
        (1, 3, 7, 5), (0, 4, 6, 2),   # top / bottom (raw z)
        (0, 1, 3, 2), (4, 6, 7, 5),   # -x / +x
        (0, 1, 5, 4), (2, 6, 7, 3),   # y-lo / y-hi
    ]
    indices = []
    for a, b, c, dd in quads:
        indices.extend([a, b, c, a, c, dd])
    # the carpet: ONE texture repeat across the width, the repeats along
    uvs = [((cy - ylo) / max(1.0, (yhi - ylo)), (cx - xlo) / 256.0) for cx, cy, cz in cs]
    mat = hint_plan[0][1] if hint_plan else 0
    return {
        "bbox_min": (xlo, ylo, zb), "bbox_max": (xhi, yhi, zt),
        "sphere": struct.unpack_from('<4f', data, start + 24),
        "verts": [(cx, cy, cz, 0.0, 0.0, 1.0) for cx, cy, cz in cs],
        "uvs": uvs,
        "indices": indices,
        "sections": [(0, 0, len(cs) - 1, len(indices) // 3,
                      len(indices) // 3)],
        "section_materials": [mat],
        "vertex_revision": 0,
    }


# The road-strip family: the meshes whose vertices live in the
# variable-length packed entries (the flat plates extracted by
# _flat_plate_mesh). The bridge border strips + the village lane strips.
_ROAD_PLATE_MESHES = set()


def convert_export(pkg_path: str, out_dir: str, only: set | None = None) -> list:
    """Convert every StaticMesh export of a package to glTF. Returns names."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from l2strict.package import Package
    from l2strict.properties import read_object

    pkg = Package.from_file(pkg_path)
    os.makedirs(out_dir, exist_ok=True)
    done = []
    for i in range(pkg.export_count):
        if pkg.class_name_of_export(i) != "StaticMesh":
            continue
        e = pkg.exports[i]
        name = pkg.name(e.object_name)
        if only and name not in only:
            continue
        try:
            # property list first: the binary bulk starts after it
            obj = read_object(
                pkg.data[e.serial_offset:e.serial_offset + e.serial_size],
                pkg, context=name, has_stack=bool(e.object_flags & 0x02000000),
            )
            bulk = e.serial_offset + obj.end
            hint = 0
            hint_plan = []
            staged_root = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), os.pardir, 'assets', 'maps',
                '20_18', 'meshes')
            staged_root = os.path.normpath(staged_root)
            for root, _dirs, files in os.walk(staged_root):
                if name + '.gltf' in files:
                    try:
                        sg = json.load(open(os.path.join(root, name + '.gltf')))
                        # the vertex hint = the UNIQUE POSITION accessors'
                        # total: UModel slices vertices per primitive, our
                        # own exports share one pool accessor across all
                        # primitives — summing per-primitive counts would
                        # multiply the pool by the prim count (9468 = 9x1052).
                        seen_acc = set()
                        for pr in sg['meshes'][0]['primitives']:
                            pa = pr['attributes']['POSITION']
                            if pa in seen_acc:
                                continue
                            seen_acc.add(pa)
                            hint += sg['accessors'][pa]['count']
                        for pr in sg['meshes'][0]['primitives']:
                            hint_plan.append((
                                sg['accessors'][pr['indices']]['count'],
                                int(pr.get('material', 0))))
                    except (json.JSONDecodeError, KeyError, OSError):
                        pass
                    break
            # The road-strip family (Btm_Obj01/02/03) stores its vertices as
            # raw 12-B positions with a constant height inside
            # variable-length packed entries — the fixed-stride run anchor
            # reads table bytes there. Extract the flat plate directly.
            if name == "O_DE_Btm_Obj01":
                # the curb assembly = the real 20-vert plate from the parse
                mesh = parse_static_mesh(pkg.data, bulk,
                        e.serial_size - obj.end, hint_verts=hint,
                        hint_plan=hint_plan, name=name)
            elif name in ("O_DE_Btm_Obj02", "O_DE_Btm_Obj03"):
                # the flat border ribbons = the single-section rectangles:
                # the bbox IS the whole mesh (the exact flat quad at the
                # z = 0 actor level), no decompression needed.
                mn = struct.unpack_from('<3f', pkg.data, bulk)
                mx = struct.unpack_from('<3f', pkg.data, bulk + 12)
                z0 = mn[2]
                cs = [(mn[0], mn[1], z0), (mx[0], mn[1], z0),
                      (mx[0], mx[1], z0), (mn[0], mx[1], z0)]
                idxs = [0, 2, 1, 0, 3, 2]
                uvs = [((c[1] - mn[1]) / 256.0, (c[0] - mn[0]) / 256.0)
                       for c in cs]
                mat = hint_plan[0][1] if hint_plan else 0
                mesh = {
                    "bbox_min": mn, "bbox_max": mx,
                    "sphere": struct.unpack_from('<4f', pkg.data, bulk + 24),
                    "verts": [(c[0], c[1], c[2], 0.0, 0.0, 1.0) for c in cs],
                    "uvs": uvs,
                    "indices": idxs,
                    "sections": [(0, 0, 3, 2, 2)],
                    "section_materials": [mat],
                    "vertex_revision": 0,
                }
                print(f"  {name}: flat border ribbon from the exact bbox")
            else:
                mesh = parse_static_mesh(pkg.data, bulk,
                                         e.serial_size - obj.end, hint_verts=hint,
                                         hint_plan=hint_plan, name=name)
                # fundamental invariant: the parsed vertices must fill the
                # file's own bbox. A mismatch = the anchor latched onto a
                # false stream. NOTE: only for the standard parse path —
                # for the road-plate family the value at bulk+0 is NOT the
                # bbox (the section tables serialize pre-bulk there), so
                # the check would be circular and is skipped.
                fmn = struct.unpack_from('<3f', pkg.data, bulk)
                fmx = struct.unpack_from('<3f', pkg.data, bulk + 12)
                vs = mesh['verts']
                vmn = [min(v[k] for v in vs) for k in range(3)]
                vmx = [max(v[k] for v in vs) for k in range(3)]
                worst = max(
                    max(abs(fmn[k] - vmn[k]), abs(fmx[k] - vmx[k]))
                    for k in range(3))
                span = max(fmx[k] - fmn[k] for k in range(3))
                if worst > max(8.0, 0.05 * max(1.0, span)):
                    raise ValueError(
                        f"vertex bbox deviates {worst:.0f} from the file bbox")
        except ValueError as ex:
            # The packed-vertex class (no f32 records at any anchor —
            # Btm_Obj01/02/03 carry the road-bed plates over the bridge and
            # the village lanes; both UModel and the anchor parser emit a
            # wrong 24-vert slab for them). Their file bounding box is
            # exact and for the road plates it is a thin slab — reconstruct
            # the plate box from the bbox corners (exact data, not a guess;
            # the real mesh is a ~0.25 m plate whose shape this box bounds).
            plate = _bbox_plate(pkg.data, bulk, hint_plan)
            if plate is None:
                print(f"  {name}: SKIPPED ({ex})")
                continue
            print(f"  {name}: bbox-plate reconstruction ({ex})")
            mesh = plate
        write_gltf(os.path.join(out_dir, name), name, mesh)
        done.append(name)
    return done


def _bbox_plate(data: bytes, bulk: int, hint_plan: list | None) -> dict | None:
    """Reconstruct a thin plate mesh from the file's exact bounding box.

    The packed-vertex road plates (O_DE_Btm_Obj01/02/03) are ~0.25 m thick
    slabs; their bbox is stored exactly at bulk+0..24 as two corners. The
    reconstruction emits an 8-corner box with planar world-scaled UVs —
    the walkable road surface and the collision match the real plate's
    bounds. Returns None when the box is not plate-like (z-span >= 2 m).

    Verts are RAW game (x, y, z) — write_gltf applies the UModel transform.
    The quad windings are derived for the glTF result (outward CCW):
    top (1,3,7,5), bottom (0,4,6,2), -x (0,1,3,2), +x (4,6,7,5),
    y-lo (0,1,5,4), y-hi (2,6,7,3).
    """
    mn = struct.unpack_from('<3f', data, bulk)
    mx = struct.unpack_from('<3f', data, bulk + 12)
    zlo, zhi = min(mn[2], mx[2]), max(mn[2], mx[2])
    if zhi - zlo >= 200.0 or zhi - zlo <= 0.0:
        return None
    xlo, xhi = min(mn[0], mx[0]), max(mn[0], mx[0])
    ylo, yhi = min(mn[1], mx[1]), max(mn[1], mx[1])
    cs = [(x, y, z) for x in (xlo, xhi) for y in (ylo, yhi) for z in (zlo, zhi)]
    quads = [
        (1, 3, 7, 5),  # top    (raw z = zhi)
        (0, 4, 6, 2),  # bottom (raw z = zlo)
        (0, 1, 3, 2),  # raw x = xlo
        (4, 6, 7, 5),  # raw x = xhi
        (0, 1, 5, 4),  # raw y = ylo
        (2, 6, 7, 3),  # raw y = yhi
    ]
    indices = []
    for a, b, c, d in quads:
        indices.extend([a, b, c, a, c, d])
    # planar UVs from the raw game XY, 2.56 m per repeat (Obase scale)
    # the carpet: ONE texture repeat across the width, the repeats along
    uvs = [((cy - ylo) / max(1.0, (yhi - ylo)), (cx - xlo) / 256.0) for cx, cy, cz in cs]
    mat = hint_plan[0][1] if hint_plan else 0
    return {
        "bbox_min": mn, "bbox_max": mx,
        "sphere": struct.unpack_from('<4f', data, bulk + 24),
        # all normals raw (0,0,1) = the plate's top: after the UModel
        # transform it becomes glTF +Y — the road surface lights correctly.
        "verts": [(cx, cy, cz, 0.0, 0.0, 1.0) for cx, cy, cz in cs],
        "uvs": uvs,
        "indices": indices,
        "sections": [(0, 0, len(cs) - 1, len(indices) // 3,
                      len(indices) // 3)],
        "section_materials": [mat],
        "vertex_revision": 0,
    }


if __name__ == "__main__":
    import sys
    pkg_path = sys.argv[1]
    out_dir = sys.argv[2]
    only = set(sys.argv[3:]) or None
    names = convert_export(pkg_path, out_dir, only)
    print(f"converted {len(names)} meshes -> {out_dir}")
