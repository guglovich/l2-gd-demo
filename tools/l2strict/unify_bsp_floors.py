#!/usr/bin/env python3
"""Unify the two 20_18 BSP floor families without a raster mask.

The client brush BSP carries a lower common DE_V_floor01 and raised native
DE_V_floor02 interiors. Their projected triangles overlap partially, so a
whole-triangle skip cannot remove the duplicate floor. This tool subtracts the
higher native footprints from each lower triangle in 2D, triangulates the
remainder, and interpolates the original height/UVs at the new vertices.

The runtime consumes the generated JSON and rebuilds only the affected brush
surfaces before rendering and collision creation. No texture, actor, or
hand-painted coverage mask is involved.

Usage:
    python3 tools/l2strict/unify_bsp_floors.py assets/maps/20_18

Requires numpy, Pillow, and shapely (the Arch system package is sufficient).
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon
from shapely.ops import unary_union

COMMON = "DE_V_floor01"
NATIVE = "DE_V_floor02"
EPS_HEIGHT = 0.02
EPS_AREA = 1e-10


def read_accessor(gltf: dict, raw: bytes, index: int) -> np.ndarray:
    acc = gltf["accessors"][index]
    view = gltf["bufferViews"][acc["bufferView"]]
    offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    data = raw[offset:offset + view["byteLength"]]
    components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    fmt = {5126: "f", 5123: "H", 5125: "I", 5121: "B"}[acc["componentType"]]
    item = struct.calcsize("<" + fmt)
    stride = view.get("byteStride", components * item)
    values: list[float] = []
    for i in range(acc["count"]):
        values.extend(struct.unpack_from("<" + fmt * components, data, i * stride))
    return np.asarray(values, dtype=np.float64).reshape(-1, components)


def load_brush(map_dir: Path, brush: dict, texture: str):
    prims = {
        int(face["prim"])
        for face in brush.get("faces", [])
        if face.get("prim") is not None
        and face.get("tex") is not None
        and face["tex"][1] == texture
    }
    if not prims:
        return None
    path = map_dir / "meshes_bsp" / f"BSP_{brush.get('polys', '')}.gltf"
    if not path.exists():
        return None
    gltf = json.loads(path.read_text())
    raw = path.with_suffix(".bin").read_bytes()
    location = np.asarray(brush.get("location", [0, 0, 0]), dtype=np.float64) * 0.01
    position = np.asarray([location[0], location[2], location[1]])
    result = []
    for surface, prim in enumerate(gltf["meshes"][0]["primitives"]):
        if surface not in prims:
            continue
        vertices = read_accessor(gltf, raw, prim["attributes"]["POSITION"])
        uvs = read_accessor(gltf, raw, prim["attributes"]["TEXCOORD_0"])
        indices = read_accessor(gltf, raw, prim["indices"]).reshape(-1, 3).astype(int)
        for tri in indices:
            a, b, c = vertices[tri]
            normal = np.cross(b - a, c - a)
            area2d = abs(float((b[0] - a[0]) * (c[2] - a[2])
                               - (b[2] - a[2]) * (c[0] - a[0])))
            if abs(float(normal[1])) < 0.01 or area2d < 1e-6:
                continue
            result.append((surface, a, b, c, uvs[tri], position))
    return result


def barycentric(point: np.ndarray, a: np.ndarray, b: np.ndarray,
                c: np.ndarray) -> tuple[float, float]:
    matrix = np.array([[b[0] - a[0], c[0] - a[0]],
                       [b[2] - a[2], c[2] - a[2]]], dtype=np.float64)
    if abs(float(np.linalg.det(matrix))) < 1e-12:
        raise ValueError(f"degenerate source triangle projection: {a}, {b}, {c}")
    u, v = np.linalg.solve(matrix, point - a[[0, 2]])
    if u < -1e-7 or v < -1e-7 or u + v > 1.0 + 1e-7:
        raise ValueError(f"clip vertex outside source triangle: {point}, uv=({u},{v})")
    return float(u), float(v)


def rounded(values: np.ndarray) -> list[float]:
    return [round(float(value), 7) for value in values]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    map_dir = Path(sys.argv[1])
    bsp = json.loads((map_dir / "bsp.json").read_text())
    native = []
    for brush in bsp.get("brushes", []):
        loaded = load_brush(map_dir, brush, NATIVE)
        if loaded:
            native.extend(loaded)

    output = {
        "build": "exact-native-floor-subtraction-v1",
        "source": {"common": COMMON, "native": NATIVE},
        "stats": {},
        "brushes": {},
    }
    total_in = 0
    total_out = 0
    total_removed = 0.0
    changed_surfaces = 0
    for brush in bsp.get("brushes", []):
        loaded = load_brush(map_dir, brush, COMMON)
        if not loaded:
            continue
        brush_name = str(brush.get("polys", ""))
        replacements: dict[str, dict] = {}
        surface_buffers: dict[int, dict] = {}
        changed_surface_ids: set[int] = set()
        for surface, a, b, c, tri_uvs, position in loaded:
            total_in += 1
            if surface not in surface_buffers:
                surface_buffers[surface] = {"vertices": [], "texcoords": []}
            buffer = surface_buffers[surface]
            world = np.array([a, b, c]) + position
            tri = Polygon([(v[0], v[2]) for v in world])
            common_y = float(world[:, 1].mean())
            covers = []
            for _, na, nb, nc, _, nposition in native:
                nworld = np.array([na, nb, nc]) + nposition
                if float(nworld[:, 1].mean()) <= common_y + EPS_HEIGHT:
                    continue
                covers.append(Polygon([(v[0], v[2]) for v in nworld]))
            if not covers:
                buffer["vertices"].extend([a, b, c])
                buffer["texcoords"].extend([tri_uvs[0], tri_uvs[1], tri_uvs[2]])
                continue
            cover = unary_union(covers)
            remainder = tri.difference(cover)
            removed = tri.area - remainder.area
            if removed <= EPS_AREA:
                buffer["vertices"].extend([a, b, c])
                buffer["texcoords"].extend([tri_uvs[0], tri_uvs[1], tri_uvs[2]])
                continue
            total_removed += removed
            changed_surface_ids.add(surface)
            vertices_out: list[np.ndarray] = []
            uvs_out: list[np.ndarray] = []
            polygons = [remainder] if remainder.geom_type == "Polygon" else list(remainder.geoms)
            for polygon in polygons:
                if polygon.is_empty or polygon.geom_type != "Polygon":
                    continue
                for clipped in constrained_delaunay_triangles(polygon).geoms:
                    coords = np.asarray(clipped.exterior.coords[:3], dtype=np.float64)
                    if Polygon(coords).area <= EPS_AREA:
                        continue
                    points = []
                    texcoords = []
                    for point in coords:
                        u, v = barycentric(point, world[0], world[1], world[2])
                        local = a + u * (b - a) + v * (c - a)
                        uv = tri_uvs[0] + u * (tri_uvs[1] - tri_uvs[0]) \
                            + v * (tri_uvs[2] - tri_uvs[0])
                        points.append(local)
                        texcoords.append(uv)
                    p0, p1, p2 = points
                    original_sign = np.sign(np.cross(b - a, c - a)[1])
                    clipped_sign = np.sign(np.cross(p1 - p0, p2 - p0)[1])
                    if clipped_sign != original_sign:
                        p1, p2 = p2, p1
                        texcoords[1], texcoords[2] = texcoords[2], texcoords[1]
                    vertices_out.extend([p0, p1, p2])
                    uvs_out.extend(texcoords)
            expected = tri.area - removed
            actual = 0.0
            for i in range(0, len(vertices_out), 3):
                p0, p1, p2 = np.array([vertices_out[i], vertices_out[i + 1],
                                       vertices_out[i + 2]]) + position
                actual += abs(float(np.cross(p1 - p0, p2 - p0)[1])) * 0.5
            if abs(actual - expected) > max(1e-7, expected * 1e-6):
                raise ValueError(f"area mismatch in {brush_name} surface {surface}: "
                                 f"{actual} != {expected}")
            buffer["vertices"].extend(vertices_out)
            buffer["texcoords"].extend(uvs_out)
        for surface in sorted(changed_surface_ids):
            buffer = surface_buffers[surface]
            replacements[str(surface)] = {
                "vertices": [coord for point in buffer["vertices"] for coord in rounded(point)],
                "texcoords": [coord for point in buffer["texcoords"] for coord in rounded(point)],
            }
            total_out += len(buffer["vertices"]) // 3
            changed_surfaces += 1
        if replacements:
            output["brushes"][brush_name] = replacements

    output["stats"] = {
        "native_triangles": len(native),
        "common_triangles": total_in,
        "replacement_triangles": total_out,
        "changed_surfaces": changed_surfaces,
        "removed_area_m2": round(total_removed, 9),
    }
    destination = map_dir / "bsp_floor_unification.json"
    destination.write_text(json.dumps(output, separators=(",", ":")) + "\n")
    print(f"bsp floor unification: {len(native)} native triangles, "
          f"{total_in} common -> {total_out} remainder triangles, "
          f"{changed_surfaces} surfaces, {total_removed:.6f} m2 removed -> {destination}")


if __name__ == "__main__":
    main()
