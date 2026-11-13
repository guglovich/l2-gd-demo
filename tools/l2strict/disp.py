#!/usr/bin/env python3
"""True displacement geometry from the height maps (the user's directive
2026-11-13: textures must have REAL polygons — forms, grooves, like
Blender-made geometry — painted afterwards with the texture colors; not a
shader-only effect).

For each planar BSP/level-BSP face this builds a tessellated grid over the
face's UV domain, samples the height field (the generated pbr_albedo A
channel), displaces the grid points along the face normal by
(h-0.5)*2*pom meters, and derives per-vertex normals from the height
gradient. The output glTF mirrors the flat mesh's prim structure (prim i ==
prim i), so world.gd renders the displaced mesh while the collision keeps
the original flat trimesh.
"""
import json
import os

import numpy as np
from PIL import Image

_cache = {}


def height_field(texroot: str, pkg: str, obj: str):
    """(height 0..1 array or None, pom meters) for a texture; None = no set.

    The albedo A channel is PAINTED SHADING (luminance), not geometry —
    displacing it at texel resolution re-renders the painted crevices as a
    physical ~45-degree sawtooth (the whole face goes blotchy-dark under the
    sun: the 2026-11-13 one-face experiment). DISPLACEMENT WANTS FORM, not
    paint: a strong gaussian separates the large forms (cobble domes, one
    per ~30-60 texels) from the paint, which stays in the albedo alone."""
    key = (pkg.lower(), obj)
    if key in _cache:
        return _cache[key]
    td = os.path.join(texroot, pkg.lower(), "Texture")
    p = os.path.join(td, obj + ".pbr_albedo.png")
    if not os.path.exists(p):
        _cache[key] = (None, 0.0)
        return _cache[key]
    side = json.load(open(os.path.join(td, obj + ".pbr.json")))
    pom = float(side.get("pom", 0.0))
    h = None
    if not side.get("alpha_mask"):  # cutout textures are not displaced
        from PIL import ImageFilter
        img = Image.open(p).split()[3]
        radius = float(side.get("form_blur", 14.0))
        img = img.filter(ImageFilter.GaussianBlur(radius))
        h = np.asarray(img).astype(np.float32) / 255.0
        hmin, hmax = float(h.min()), float(h.max())
        h = (h - hmin) / max(1e-6, hmax - hmin)
    _cache[key] = (h, pom)
    return _cache[key]


def sample_bilinear(h: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    hh, hw = h.shape
    u = np.mod(u, hw)
    v = np.mod(v, hh)
    u0 = np.floor(u).astype(np.int64)
    v0 = np.floor(v).astype(np.int64)
    u1 = np.minimum(u0 + 1, hw - 1)
    v1 = np.minimum(v0 + 1, hh - 1)
    fu = (u - u0)[..., None]
    fv = (v - v0)[..., None]
    a = h[v0, u0][..., None] * (1 - fu) * (1 - fv)
    b = h[v0, u1][..., None] * fu * (1 - fv)
    c = h[v1, u0][..., None] * (1 - fu) * fv
    d = h[v1, u1][..., None] * fu * fv
    return (a + b + c + d)[..., 0]


def point_in_poly(px: np.ndarray, py: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """even-odd ray casting, vectorized; poly = (n,2) uv-domain polygon"""
    inside = np.zeros(px.shape, dtype=bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = ((y1 > py) != (y2 > py))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1
        inside ^= cond & (px < xint)
    return inside


def displace_poly(verts3d, uvs_px, h, pom, max_points=15000, step0=6.0,
                  outward=None):
    """Tessellate one polygon with height displacement.

    verts3d: (n,3) float; uvs_px: (n,2) texel coords (any translation — the
    fit absorbs it). outward: a hint direction (face centroid minus the brush
    bbox center) — the glTF winding of BSP faces is not reliable, so the
    displacement normal is flipped to the outward side; wrong sign would
    carve pits instead of bumps AND point the vertex normals inward.
    Returns (pos, uv, nrm, idx) flat arrays, or None."""
    verts3d = np.asarray(verts3d, dtype=np.float64)
    uvs_px = np.asarray(uvs_px, dtype=np.float64)
    n = len(verts3d)
    if n < 3:
        return None
    # affine fit world = M @ [u, v, 1]
    A = np.concatenate([uvs_px, np.ones((n, 1))], axis=1)
    M, *_ = np.linalg.lstsq(A, verts3d, rcond=None)
    # plane normal from the polygon
    nv = verts3d - verts3d.mean(axis=0)
    _, sv, vt = np.linalg.svd(nv, full_matrices=False)
    N = vt[2]
    if np.linalg.norm(np.cross(verts3d[1] - verts3d[0], verts3d[2] - verts3d[0])) < 1e-9:
        return None
    N = np.cross(verts3d[1] - verts3d[0], verts3d[2] - verts3d[0])
    ln = np.linalg.norm(N)
    if ln < 1e-9:
        return None
    N = N / ln
    if outward is not None and float(np.dot(N, np.asarray(outward))) < 0.0:
        N = -N
    Bu = M[0, :]   # world step per +1 texel u (meters); M solves A@M=verts,
    Bv = M[1, :]   # so the world axes are the COLUMNS of M (rows k = the
                   # u/v/1 coefficients). The old M[:,0] transpose produced a
                   # scrambled world for every face whose UV base was not the
                   # world origin (the canonical UVs exposed it).

    lo = uvs_px.min(axis=0)
    hi = uvs_px.max(axis=0)
    span = hi - lo
    step = float(step0)
    while True:
        gx = max(2, int(np.ceil(span[0] / step)) + 1)
        gy = max(2, int(np.ceil(span[1] / step)) + 1)
        if gx * gy <= max_points or step > 4096:
            break
        step *= 2.0
    us = np.linspace(lo[0], hi[0], gx)
    vs = np.linspace(lo[1], hi[1], gy)
    UU, VV = np.meshgrid(us, vs)
    P = np.stack([UU.ravel(), VV.ravel()], axis=1)
    inside = point_in_poly(P[:, 0], P[:, 1], uvs_px)
    if not inside.any():
        return None
    # every grid point on the uv bbox grid keeps a regular lattice; outside
    # points are dropped, indices only connect inside quads (all 4 corners)
    gi = -np.ones(len(P), dtype=np.int64)
    gi[inside] = np.arange(int(inside.sum()))
    iX = P[inside]
    idx_map = gi.reshape(gy, gx)

    # height + gradient (central differences over the height field)
    hv = sample_bilinear(h, iX[:, 0], iX[:, 1])
    gxu = (sample_bilinear(h, iX[:, 0] + 1, iX[:, 1]) -
           sample_bilinear(h, iX[:, 0] - 1, iX[:, 1])) * 0.5
    gyv = (sample_bilinear(h, iX[:, 0], iX[:, 1] + 1) -
           sample_bilinear(h, iX[:, 0], iX[:, 1] - 1)) * 0.5

    world = np.concatenate([iX, np.ones((len(iX), 1))], axis=1) @ M
    # UPWARD-ONLY displacement (0..pom): the plate plane = the mortar level.
    # The old +-pom made the surface DIP below the coplanar LevelBSP slab
    # underneath, exposing its broken UV stream as black blobs; upward-only
    # also removes the coplanar z-fight the flat baseline had.
    disp = hv * pom
    world = world + N[None, :] * disp[:, None]
    # normal = plane normal minus the displacement gradient (tangential)
    grad = Bu[None, :] * (gxu * pom)[:, None] + \
        Bv[None, :] * (gyv * pom)[:, None]
    nrm = N[None, :] - grad
    nrm /= np.maximum(1e-9, np.linalg.norm(nrm, axis=1))[:, None]

    # quad indices over the regular lattice (4 inside corners)
    quads = []
    for r in range(gy - 1):
        for c in range(gx - 1):
            a = idx_map[r, c]
            b = idx_map[r, c + 1]
            cc = idx_map[r + 1, c + 1]
            d = idx_map[r + 1, c]
            if a >= 0 and b >= 0 and cc >= 0 and d >= 0:
                quads.append((a, b, cc, d))
    if not quads:
        return None
    idx = []
    for a, b, cc, d in quads:
        idx.extend([a, b, cc, a, cc, d])
    # Winding must face OUTWARD: Godot generates the flat per-face normals
    # from the triangle winding (the mesh carries no NORMAL attribute), and
    # with cull_disabled the renderer does not flip them for backfaces — a
    # wrong winding made the whole displaced plate render unlit-black.
    wv = world[idx[:3]]
    fn = np.cross(wv[1] - wv[0], wv[2] - wv[0])
    if outward is not None and float(np.dot(fn, np.asarray(outward))) < 0.0:
        idx = [j for k in range(0, len(idx), 3) for j in
               (idx[k], idx[k + 2], idx[k + 1])]
    return world, iX, nrm, np.asarray(idx, dtype=np.int64)


def write_displaced_gltf(path: str, name: str, prims_data: list) -> bool:
    """prims_data: list aligned with the flat mesh's prims; each item is
    either None (-> flat copy impossible here; caller must skip the prim) or
    a dict {pos, uv, nrm, idx}. Writes <path>_D.gltf + .bin."""
    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    mesh_prims = []
    for si, item in enumerate(prims_data):
        if item is None:
            return False
        pos = item["pos"].astype(np.float32).ravel()
        uv = item["uv"].astype(np.float32).ravel()
        idx = item["idx"].astype(np.uint32).ravel()
        if len(idx) == 0:
            return False
        # NO NORMAL attribute: Godot generates flat per-face normals from the
        # winding — the same mechanism the flat mesh (which renders lit)
        # uses. The height-gradient vertex normals made the displaced surface
        # render dark under identical lighting (2026-11-13 experiment); the
        # micro-relief shading belongs to the normal map anyway.
        for arr, ctype, vtype, comp in ((pos, 5126, "VEC3", 3), (uv, 5126, "VEC2", 2)):
            b = arr.tobytes()
            buffer_views.append({"buffer": 0, "byteOffset": len(blob),
                                 "byteLength": len(b)})
            blob.extend(b)
            acc = {"bufferView": len(buffer_views) - 1,
                   "componentType": ctype, "count": len(arr) // comp,
                   "type": vtype}
            if vtype == "VEC3" and arr is pos:
                p3 = pos.reshape(-1, 3)
                acc["min"] = [float(p3[:, k].min()) for k in range(3)]
                acc["max"] = [float(p3[:, k].max()) for k in range(3)]
            accessors.append(acc)
        b = idx.tobytes()
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(b)})
        blob.extend(b)
        accessors.append({"bufferView": len(buffer_views) - 1,
                          "componentType": 5125, "count": len(idx),
                          "type": "SCALAR"})
        while len(blob) % 4:
            blob.append(0)
        materials.append({"name": f"m{si}", "pbrMetallicRoughness":
                          {"baseColorFactor": [0.4, 0.4, 0.4, 1.0]},
                          "doubleSided": True})
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 3,
                                          "TEXCOORD_0": len(accessors) - 2},
                           "indices": len(accessors) - 1,
                           "material": si, "mode": 4})
    gltf = {
        "asset": {"version": "2.0", "generator": "l2godot displace"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name + "_D"}],
        "meshes": [{"name": name + "_D", "primitives": mesh_prims}],
        "materials": materials,
        "accessors": accessors, "bufferViews": buffer_views,
        "buffers": [{"uri": name + "_D.bin", "byteLength": len(blob)}],
    }
    json.dump(gltf, open(path + "_D.gltf", "w"))
    open(path + "_D.bin", "wb").write(bytes(blob))
    return True
