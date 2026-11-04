"""Build exact terrain height, visibility, edge-turn, and layer data."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .errors import AssetError
from .extract import extract_terrain
from .package import PackageSet


@dataclass(slots=True)
class Heightfield:
    width: int
    height: int
    origin: tuple[float, float, float]
    scale: tuple[float, float, float]
    raw: np.ndarray
    edge_turn: np.ndarray

    def covers(self, world_x: float, world_y: float) -> bool:
        local_x = (world_x - self.origin[0]) / self.scale[0]
        local_y = (world_y - self.origin[1]) / self.scale[1]
        return (
            local_x >= -1e-6
            and local_y >= -1e-6
            and local_x <= self.width - 1 + 1e-6
            and local_y <= self.height - 1 + 1e-6
        )

    def raw_at(self, x: int, y: int) -> float:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            raise AssetError(f"height sample outside field: {x},{y}")
        return float(self.raw[y, x])

    def sample(self, world_x: float, world_y: float) -> float:
        local_x = (world_x - self.origin[0]) / self.scale[0]
        local_y = (world_y - self.origin[1]) / self.scale[1]
        gx = min(max(local_x, 0.0), float(self.width - 1))
        gy = min(max(local_y, 0.0), float(self.height - 1))
        ix = min(int(np.floor(gx)), self.width - 2)
        iy = min(int(np.floor(gy)), self.height - 2)
        fx = gx - ix
        fy = gy - iy

        a = self.raw_at(ix, iy)
        b = self.raw_at(ix + 1, iy)
        c = self.raw_at(ix, iy + 1)
        d = self.raw_at(ix + 1, iy + 1)

        if bool(self.edge_turn[iy, ix]):
            if fy <= fx:
                raw = a + (b - a) * fx + (d - b) * fy
            else:
                raw = a + (d - c) * fx + (c - a) * fy
        else:
            if fx + fy <= 1.0:
                raw = a + (b - a) * fx + (c - a) * fy
            else:
                raw = d + (c - d) * (1.0 - fx) + (b - d) * (1.0 - fy)
        return float(raw * self.scale[2] + self.origin[2])


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _decode_bitset(data: bytes, name: str, width: int, height: int) -> np.ndarray:
    required = (width * height + 7) // 8
    if len(data) < required:
        raise AssetError(
            f"{name}: bitset has {len(data)} bytes, needs at least {required}"
        )
    bits = np.frombuffer(data[:required], dtype=np.uint8)
    indices = np.arange(width * height, dtype=np.uint32)
    bytes_ = bits[indices // 8]
    masks = np.uint8(1) << (indices % 8).astype(np.uint8)
    return ((bytes_ & masks) != 0).astype(np.uint8).reshape(height, width)


def _canonical_ref(ref: dict | None, pool: PackageSet) -> dict | None:
    if ref is None:
        return None
    package = pool.get(ref["package"])
    return {
        "package": package.package_name if package else ref["package"],
        "owner": ref["package"],
        "object": ref["object"],
        "class": ref["class"],
        "kind": ref["kind"],
        "outer_chain": ref.get("outer_chain", []),
    }


def _read_height_texture(
    pool: PackageSet,
    ref: dict,
    *,
    context: str,
) -> tuple[np.ndarray, int, int]:
    package = pool.get(ref["package"])
    if package is None:
        raise AssetError(f"{context}: heightmap package is not staged: {ref['package']}")
    index = package.export_by_name(ref["object"], "Texture")
    if index is None:
        raise AssetError(
            f"{context}: heightmap Texture {ref['package']}:{ref['object']} not found"
        )
    data = package.export_data(index)
    if len(data) < 10:
        raise AssetError(f"{context}: heightmap object is too small")
    width, height = struct.unpack_from("<II", data, len(data) - 10)
    u_bits = data[len(data) - 2]
    v_bits = data[len(data) - 1]
    if width < 2 or height < 2 or width > 4096 or height > 4096:
        raise AssetError(f"{context}: invalid heightmap dimensions {width}x{height}")
    if u_bits != 8 or v_bits != 8:
        raise AssetError(
            f"{context}: unsupported heightmap bit depth {u_bits}/{v_bits}"
        )
    data_len = width * height * 2
    offset = len(data) - 10 - data_len
    if offset < 0:
        raise AssetError(
            f"{context}: heightmap payload {data_len} exceeds object size {len(data)}"
        )
    raw = np.frombuffer(data, dtype="<u2", count=width * height, offset=offset)
    raw = raw.reshape(height, width)
    if not np.isfinite(raw).all():
        raise AssetError(f"{context}: non-finite raw heightmap value")
    return raw, width, height


def _field_from_terrain(
    pool: PackageSet,
    terrain: dict,
    *,
    context: str,
) -> Heightfield:
    terrain_map = terrain["terrain_map"]
    raw, width, height = _read_height_texture(pool, terrain_map, context=context)
    terrain_scale = terrain["terrain_scale"]
    if terrain_scale[0] == 0.0 or terrain_scale[1] == 0.0 or terrain_scale[2] == 0.0:
        raise AssetError(f"{context}: broken TerrainScale {terrain_scale}")
    scale = (
        float(terrain_scale[0]),
        float(terrain_scale[1]),
        float(terrain_scale[2]) / 256.0,
    )
    location = terrain["location"]
    origin = (
        float(location[0]) - width / 2.0 * scale[0],
        float(location[1]) - height / 2.0 * scale[1],
        float(location[2]) - 32768.0 * scale[2],
    )
    if abs(width * scale[0] - 32768.0) > 0.01:
        raise AssetError(
            f"{context}: terrain width {width} * X scale {scale[0]} != 32768"
        )
    if abs(height * scale[1] - 32768.0) > 0.01:
        raise AssetError(
            f"{context}: terrain height {height} * Y scale {scale[1]} != 32768"
        )
    edge_data = base64.b64decode(terrain["edge_turn_bitmap_b64"])
    edge = _decode_bitset(edge_data, f"{context}.EdgeTurnBitmap", width, height)
    return Heightfield(
        width=width,
        height=height,
        origin=origin,
        scale=scale,
        raw=raw,
        edge_turn=edge,
    )


def _layer_mapping(terrain: dict, layer: dict) -> dict:
    scale = layer["scale"]
    u_scale = layer["u_scale"]
    v_scale = layer["v_scale"]
    location = terrain["location"]
    verified = (
        terrain["terrain_scale"][0] == 128.0
        and terrain["terrain_scale"][1] == 128.0
        and layer["texture_map_axis"] == 0
        and layer["u_pan"] == 0.0
        and layer["v_pan"] == 0.0
        and layer["texture_rotation"] == 0.0
        and layer["layer_rotation"] == [0, 0, 0]
        and u_scale > 0.0
        and v_scale > 0.0
        and scale[0] > 0.0
        and scale[1] > 0.0
    )
    su = 2.0 * scale[0] / (128.0 * 128.0 * u_scale)
    sv = 2.0 * scale[1] / (128.0 * 128.0 * v_scale)
    x0 = float(location[0]) - 16384.0
    y0 = float(location[1]) - 16384.0
    return {
        "verified": verified,
        "uv_scale": [su, sv],
        "uv_offset": [-x0 * su, -y0 * sv],
        "mask_uv": [0.0, 0.0, 1.0, 1.0],
    }


def _load_neighbor(
    pool: PackageSet, map_path: str
) -> tuple[dict, Heightfield]:
    terrain = extract_terrain(map_path)
    field = _field_from_terrain(
        pool, terrain, context=f"{Path(map_path).stem}:TerrainInfo:{terrain['name']}"
    )
    return terrain, field


def build_terrain(
    *,
    work_dir: str,
    map_data: dict,
    pool: PackageSet,
    neighbors: tuple[tuple[str, str], ...] = (),
) -> dict:
    """Write exact terrain data and return the terrain metadata.

    ``neighbors`` is a sequence of ``(map_name, staged_map_path)`` pairs.  The
    caller is responsible for staging the corresponding maps and heightmap
    texture packages first.
    """
    terrain = map_data["terrain"]
    owner = _field_from_terrain(
        pool, terrain, context=f"{map_data['map']}:TerrainInfo:{terrain['name']}"
    )
    width, height = owner.width, owner.height

    visibility_data = base64.b64decode(terrain["quad_visibility_bitmap_b64"])
    edge_data = base64.b64decode(terrain["edge_turn_bitmap_b64"])
    surface_present = _decode_bitset(
        visibility_data, "QuadVisibilityBitmap", width, height
    )
    edge_turn = _decode_bitset(edge_data, "EdgeTurnBitmap", width, height)
    if not np.array_equal(owner.edge_turn, edge_turn):
        raise AssetError("EdgeTurnBitmap decoded inconsistently")

    neighbor_fields: list[Heightfield] = []
    neighbor_terrains: list[dict] = []
    for name, path in neighbors:
        neighbor_terrain, field = _load_neighbor(pool, path)
        if field.width != width or field.height != height:
            raise AssetError(
                f"neighbor {name} has terrain dimensions {field.width}x{field.height}, "
                f"expected {width}x{height}"
            )
        neighbor_terrains.append(neighbor_terrain)
        neighbor_fields.append(field)

    east = next((f for f in neighbor_fields if abs(f.origin[0] - (owner.origin[0] + width * owner.scale[0])) < 0.01 and abs(f.origin[1] - owner.origin[1]) < 0.01), None)
    south = next((f for f in neighbor_fields if abs(f.origin[1] - (owner.origin[1] + height * owner.scale[1])) < 0.01 and abs(f.origin[0] - owner.origin[0]) < 0.01), None)
    southeast = next(
        (
            f
            for f in neighbor_fields
            if abs(f.origin[0] - (owner.origin[0] + width * owner.scale[0])) < 0.01
            and abs(f.origin[1] - (owner.origin[1] + height * owner.scale[1])) < 0.01
        ),
        None,
    )

    heights = np.zeros((height + 1, width + 1), dtype="<f4")
    clamped = 0
    warnings: list[str] = []

    for y in range(height + 1):
        for x in range(width + 1):
            world_x = owner.origin[0] + x * owner.scale[0]
            world_y = owner.origin[1] + y * owner.scale[1]
            if x < width and y < height:
                heights[y, x] = owner.raw_at(x, y) * owner.scale[2] + owner.origin[2]
                continue

            preferred = None
            if x == width and y < height:
                preferred = east
            elif y == height and x < width:
                preferred = south
            elif x == width and y == height:
                preferred = southeast

            source = None
            if preferred is not None and preferred.covers(world_x, world_y):
                source = preferred
            else:
                for field in (east, south, southeast, owner):
                    if field is not None and field.covers(world_x, world_y):
                        source = field
                        break
            if source is None:
                source = preferred if preferred is not None else owner
                clamped += 1
            heights[y, x] = source.sample(world_x, world_y)

    if clamped:
        warnings.append(
            f"{clamped} terrain border sample(s) clamped to available heightmaps"
        )
    if east is None:
        warnings.append("east terrain neighbour unavailable")
    if south is None:
        warnings.append("south terrain neighbour unavailable")
    if southeast is None:
        warnings.append("southeast terrain neighbour unavailable")
    if not np.isfinite(heights).all():
        raise AssetError("non-finite world terrain height")

    layers = []
    for layer in terrain["layers"]:
        if layer["texture"] is None and layer["alpha_map"] is None:
            continue
        mapping = _layer_mapping(terrain, layer)
        layers.append(
            {
                "slot": layer["slot"],
                "texture": _canonical_ref(layer["texture"], pool),
                "mask": _canonical_ref(layer["alpha_map"], pool),
                "u_scale": layer["u_scale"],
                "v_scale": layer["v_scale"],
                "u_pan": layer["u_pan"],
                "v_pan": layer["v_pan"],
                "texture_map_axis": layer["texture_map_axis"],
                "texture_rotation": layer["texture_rotation"],
                "layer_rotation": layer["layer_rotation"],
                "scale": layer["scale"],
                "use_alpha": layer["use_alpha"],
                "mapping": mapping,
            }
        )

    terrain_dir = os.path.join(work_dir, "terrain")
    os.makedirs(terrain_dir, exist_ok=True)
    outputs: dict[str, str] = {}

    source_raw_path = os.path.join(terrain_dir, "height_source_g16.raw")
    with open(source_raw_path, "wb") as fp:
        fp.write(owner.raw.astype("<u2").tobytes(order="C"))
    outputs["height_source_g16"] = source_raw_path

    world_height_path = os.path.join(terrain_dir, "height_world_f32.raw")
    with open(world_height_path, "wb") as fp:
        fp.write(heights.astype("<f4", copy=False).tobytes(order="C"))
    outputs["height_world_f32"] = world_height_path

    surface_path = os.path.join(terrain_dir, "surface_present_u8.raw")
    with open(surface_path, "wb") as fp:
        fp.write(surface_present.astype(np.uint8).tobytes(order="C"))
    outputs["surface_present_u8"] = surface_path

    edge_path = os.path.join(terrain_dir, "edge_turn_u8.raw")
    with open(edge_path, "wb") as fp:
        fp.write(edge_turn.astype(np.uint8).tobytes(order="C"))
    outputs["edge_turn_u8"] = edge_path

    preview_path = os.path.join(terrain_dir, "heightmap_preview.png")
    try:
        from PIL import Image

        preview = (
            (owner.raw.astype(np.float32) - float(owner.raw.min()))
            / max(1.0, float(owner.raw.max() - owner.raw.min()))
            * 255.0
        ).astype(np.uint8)
        Image.fromarray(preview).save(preview_path)
        outputs["heightmap_preview_png"] = preview_path
    except ImportError:
        pass

    metadata = {
        "schema": "l2-terrain-export-v1",
        "map": map_data["map"],
        "terrain_info": terrain["name"],
        "source_height_size": [width, height],
        "height_world_size": [width + 1, height + 1],
        "cell_size_game_xy": [owner.scale[0], owner.scale[1]],
        "origin_game_xy": [owner.origin[0], owner.origin[1]],
        "origin_game_z": owner.origin[2],
        "extent_game_xy": [width * owner.scale[0], height * owner.scale[1]],
        "terrain_scale": terrain["terrain_scale"],
        "location": terrain["location"],
        "map_x": terrain["map_x"],
        "map_y": terrain["map_y"],
        "height_encoding": "float32-le",
        "height_semantics": "absolute-game-z",
        "row_order": "increasing-game-y",
        "column_order": "increasing-game-x",
        "surface_present_encoding": "uint8-0-hole-1-surface",
        "edge_turn_encoding": "uint8-0-or-1",
        "border_policy": "sample-neighbours-in-world-coordinates",
        "clamped_border_samples": clamped,
        "visible_quad_count": int(surface_present.sum()),
        "hole_quad_count": int(surface_present.size - surface_present.sum()),
        "edge_turn_quad_count": int(edge_turn.sum()),
        "height_min": float(heights.min()),
        "height_max": float(heights.max()),
        "layers": layers,
        "warnings": warnings,
        "neighbours": [
            {
                "map": name,
                "origin": list(field.origin),
                "scale": list(field.scale),
                "terrain_info": neighbor["name"],
            }
            for name, neighbor, field in zip(
                [item[0] for item in neighbors],
                neighbor_terrains,
                neighbor_fields,
                strict=True,
            )
        ],
        "files": {
            key: {
                "path": path,
                "sha256": _sha256_file(path),
                "size": os.path.getsize(path),
            }
            for key, path in outputs.items()
        },
    }

    metadata_path = os.path.join(terrain_dir, "terrain.json")
    with open(metadata_path, "w", encoding="utf-8") as fp:
        json.dump(metadata, fp, indent=2)
        fp.write("\n")
    return metadata
