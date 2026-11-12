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
    """(height 0..1 array or None, pom meters) for a texture; None = no set"""
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
        h = np.asarray(Image.open(p))[..., 3].astype(np.float32) / 255.0
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


def displace_poly(verts3d, uvs_px, h, pom, max_points=15000, step0=6.0):
    """Tessellate one polygon with height displacement.

    verts3d: (n,3) float; uvs_px: (n,2) texel coords (any translation — the
    fit absorbs it). Returns (pos, uv, nrm, idx) flat arrays, or None."""
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
    Bu = M[:, 0]   # world step per +1 texel u (meters)
    Bv = M[:, 1]

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

    world = iX @ M[:, :2].T + M[:, 2]
    disp = (hv - 0.5) * 2.0 * pom
    world = world + N[None, :] * disp[:, None]
    # normal = plane normal minus the displacement gradient (tangential)
    grad = Bu[None, :] * (gxu * 2.0 * pom)[:, None] + \
        Bv[None, :] * (gyv * 2.0 * pom)[:, None]
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
        nrm = item["nrm"].astype(np.float32).ravel()
        idx = item["idx"].astype(np.uint32).ravel()
        if len(idx) == 0:
            return False
        for arr, ctype, vtype, comp in ((pos, 5126, "VEC3", 3), (uv, 5126, "VEC2", 2),
                                        (nrm, 5126, "VEC3", 3)):
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
        mesh_prims.append({"attributes": {"POSITION": len(accessors) - 4,
                                          "TEXCOORD_0": len(accessors) - 3,
                                          "NORMAL": len(accessors) - 2},
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
