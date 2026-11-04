"""Strict extraction of an L2 map package into a JSON-ready dictionary."""

from __future__ import annotations

import base64
import hashlib
import os
from collections import Counter
from typing import Any

from . import SCHEMA_VERSION
from .errors import ExtractionError
from .package import Package, ResolvedRef
from .properties import RawBytes, read_object

ACTOR_CLASSES = {"StaticMeshActor", "PlayerStart", "Light"}
TERRAIN_CLASSES = {"TerrainInfo"}
LEGACY_CLASSES = {"TerrainSector"}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _vec(value: Any, default: tuple[float, float, float]) -> list[float]:
    if value is None:
        return list(default)
    if isinstance(value, (tuple, list)):
        if len(value) != 3:
            raise ExtractionError(f"invalid vector value {value!r}")
        return [float(value[0]), float(value[1]), float(value[2])]
    raise ExtractionError(f"invalid vector value {value!r}")


def _rot(value: Any) -> list[int]:
    if value is None:
        return [0, 0, 0]
    if isinstance(value, (tuple, list)):
        if len(value) != 3:
            raise ExtractionError(f"invalid rotator value {value!r}")
        return [int(value[0]), int(value[1]), int(value[2])]
    raise ExtractionError(f"invalid rotator value {value!r}")


def _ref(ref: Any, package: Package) -> dict | None:
    if ref in (None, 0):
        return None
    if not isinstance(ref, int):
        raise ExtractionError(f"invalid object reference {ref!r}")
    resolved = package.resolve_ref(ref)
    if resolved is None:
        return None
    return {
        "package": resolved.package,
        "object": resolved.object,
        "class": resolved.class_name,
        "kind": resolved.kind,
        "outer_chain": resolved.outer_chain,
        "raw": resolved.ref,
    }


def _bytes(value: Any, name: str) -> bytes:
    if isinstance(value, RawBytes):
        return bytes(value.data)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, list):
        if not value:
            raise ExtractionError(f"{name}: empty bitset array")
        if all(isinstance(v, int) for v in value):
            # L2 stores bitsets as arrays of signed 32-bit words; pack them
            # back into the byte order used by Unreal's FBitSet.
            if len(value) * 4 >= 1 << 20:
                raise ExtractionError(f"{name}: implausible bitset word count")
            return b"".join(int(v).to_bytes(4, "little", signed=True) for v in value)
    raise ExtractionError(f"{name}: unsupported bitset value {type(value).__name__}")


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _layer(slot: int, values: dict[str, Any], package: Package) -> dict:
    texture_ref = values.get("Texture", 0)
    alpha_ref = values.get("AlphaMap", 0)
    matrix = values.get("TerrainMatrix")
    return {
        "slot": slot,
        "texture": _ref(texture_ref, package),
        "alpha_map": _ref(alpha_ref, package),
        "u_scale": float(values.get("UScale", 1.0)),
        "v_scale": float(values.get("VScale", 1.0)),
        "u_pan": float(values.get("UPan", 0.0)),
        "v_pan": float(values.get("VPan", 0.0)),
        "texture_map_axis": int(values.get("TextureMapAxis", 0)),
        "texture_rotation": float(values.get("TextureRotation", 0.0)),
        "layer_rotation": _rot(values.get("LayerRotation")),
        "scale": _vec(values.get("Scale"), (1.0, 1.0, 1.0)),
        "terrain_matrix": matrix if isinstance(matrix, dict) else None,
        "k_friction": float(values.get("KFriction", 0.0)),
        "k_restitution": float(values.get("KRestitution", 0.0)),
        "layer_weight_map": int(values.get("LayerWeightMap", 0)),
        "use_alpha": bool(values.get("bUseAlpha", False)),
    }


def _actor(
    package: Package,
    export_index: int,
    class_name: str,
    object_name: str,
    props: dict[str, Any],
    trailing: int,
    context: str,
) -> dict:
    if trailing != 0:
        raise ExtractionError(
            f"{context}: actor object has {trailing} trailing byte(s); expected 0"
        )
    mesh_ref = props.get("StaticMesh", 0)
    deleted = bool(props.get("bDeleteMe", False))
    if class_name == "StaticMeshActor" and mesh_ref == 0 and not deleted:
        raise ExtractionError(
            f"{context}: StaticMeshActor has no StaticMesh reference and is not deleted"
        )

    record = {
        "index": export_index,
        "class": class_name,
        "name": object_name,
        "deleted": deleted,
        "hidden": bool(props.get("bHidden", False)),
        "location": _vec(props.get("Location"), (0.0, 0.0, 0.0)),
        "rotation": _rot(props.get("Rotation")),
        "draw_scale": float(props.get("DrawScale", 1.0)),
        "draw_scale3d": _vec(props.get("DrawScale3D"), (1.0, 1.0, 1.0)),
        "pre_pivot": _vec(props.get("PrePivot"), (0.0, 0.0, 0.0)),
        "mesh": _ref(mesh_ref, package),
    }
    if class_name == "Light":
        color = props.get("LightColor")
        if isinstance(color, dict):
            record["light_color"] = [
                float(color.get("R", color.get("r", 255))),
                float(color.get("G", color.get("g", 255))),
                float(color.get("B", color.get("b", 255))),
            ]
        record["light_brightness"] = float(props.get("LightBrightness", 255.0))
        record["light_radius"] = float(props.get("LightRadius", 128.0))
        record["light_saturation"] = float(props.get("LightSaturation", 0.0))
        record["light_type"] = int(props.get("LightType", 1))
    return record


def _terrain(
    package: Package,
    export_index: int,
    object_name: str,
    props: dict[str, Any],
    trailing: int,
    context: str,
) -> dict:
    layers_value = props.get("Layers")
    if isinstance(layers_value, dict):
        layers_value = [layers_value]
    if not isinstance(layers_value, list):
        raise ExtractionError(f"{context}: Layers is not an array")
    layers = [
        _layer(slot, layer, package)
        for slot, layer in enumerate(layers_value)
        if isinstance(layer, dict)
    ]
    valid_layers = [
        layer for layer in layers if layer["texture"] is not None or layer["alpha_map"] is not None
    ]

    terrain_map = _ref(props.get("TerrainMap", 0), package)
    if terrain_map is None:
        raise ExtractionError(f"{context}: TerrainInfo has no TerrainMap")
    terrain_scale = _vec(props.get("TerrainScale"), (0.0, 0.0, 0.0))
    if terrain_scale[0] == 0.0 or terrain_scale[1] == 0.0 or terrain_scale[2] == 0.0:
        raise ExtractionError(f"{context}: broken TerrainScale {terrain_scale}")

    quad_visibility = _bytes(props.get("QuadVisibilityBitmap"), f"{context}.QuadVisibilityBitmap")
    edge_turn = _bytes(props.get("EdgeTurnBitmap"), f"{context}.EdgeTurnBitmap")

    return {
        "index": export_index,
        "name": object_name,
        "terrain_map": terrain_map,
        "terrain_scale": terrain_scale,
        "location": _vec(props.get("Location"), (0.0, 0.0, 0.0)),
        "draw_scale": float(props.get("DrawScale", 1.0)),
        "map_x": int(props.get("MapX", 0)),
        "map_y": int(props.get("MapY", 0)),
        "layers": layers,
        "layer_count": len(layers),
        "valid_layer_count": len(valid_layers),
        "quad_visibility_bitmap_b64": _b64(quad_visibility),
        "edge_turn_bitmap_b64": _b64(edge_turn),
        "trailing_bytes": trailing,
    }


def extract_terrain(path: str) -> dict:
    """Extract only the single TerrainInfo export from a map package.

    Neighbour maps are used for border height sampling.  They may contain
    legacy or damaged actor data that is irrelevant to terrain, so this path
    intentionally does not apply the full actor gates.
    """
    package = Package.from_file(path)
    terrains: list[dict] = []
    errors: list[str] = []

    for index in range(package.export_count):
        if package.class_name_of_export(index) != "TerrainInfo":
            continue
        export = package.exports[index]
        object_name = package.name(export.object_name)
        context = f"{package.package_name}:{object_name}"
        data = package.export_data(index)
        try:
            parsed = read_object(
                data,
                package,
                context=context,
                has_stack=bool(export.object_flags & 0x02000000),
            )
            terrains.append(
                _terrain(
                    package,
                    index,
                    object_name,
                    parsed.props.values,
                    parsed.trailing,
                    context,
                )
            )
        except Exception as exc:
            errors.append(f"{context}: {type(exc).__name__}: {exc}")

    if errors:
        raise ExtractionError(
            f"{os.path.basename(path)}: {len(errors)} terrain extraction error(s):\n"
            + "\n".join(errors)
        )
    if len(terrains) != 1:
        raise ExtractionError(
            f"{os.path.basename(path)}: expected exactly one TerrainInfo, got "
            f"{len(terrains)}"
        )
    return terrains[0]


def extract_map(
    path: str,
    *,
    expected_counts: dict[str, int] | None = None,
) -> dict:
    package = Package.from_file(path)
    class_counts: Counter[str] = Counter()
    actors: list[dict] = []
    terrains: list[dict] = []
    errors: list[str] = []

    for index in range(package.export_count):
        class_name = package.class_name_of_export(index)
        class_counts[class_name] += 1
        if class_name in LEGACY_CLASSES:
            continue
        if class_name not in ACTOR_CLASSES and class_name not in TERRAIN_CLASSES:
            continue

        export = package.exports[index]
        object_name = package.name(export.object_name)
        context = f"{package.package_name}:{object_name}"
        data = package.export_data(index)
        try:
            parsed = read_object(
                data,
                package,
                context=context,
                has_stack=bool(export.object_flags & 0x02000000),
            )
            values = parsed.props.values
            if class_name in ACTOR_CLASSES:
                actors.append(
                    _actor(
                        package,
                        index,
                        class_name,
                        object_name,
                        values,
                        parsed.trailing,
                        context,
                    )
                )
            else:
                terrains.append(
                    _terrain(
                        package,
                        index,
                        object_name,
                        values,
                        parsed.trailing,
                        context,
                    )
                )
        except Exception as exc:
            errors.append(f"{context}: {type(exc).__name__}: {exc}")

    if errors:
        raise ExtractionError(
            f"{os.path.basename(path)}: {len(errors)} strict extraction error(s):\n"
            + "\n".join(errors)
        )
    if len(terrains) != 1:
        raise ExtractionError(
            f"{os.path.basename(path)}: expected exactly one TerrainInfo, got "
            f"{len(terrains)}"
        )

    if expected_counts:
        for class_name, expected in expected_counts.items():
            actual = class_counts[class_name]
            if actual != expected:
                raise ExtractionError(
                    f"{os.path.basename(path)}: expected {expected} "
                    f"{class_name} exports, got {actual}"
                )

    mesh_deps: dict[str, set[str]] = {}
    texture_deps: dict[str, set[str]] = {}
    for actor in actors:
        mesh = actor.get("mesh")
        if mesh is None:
            continue
        mesh_deps.setdefault(mesh["package"], set()).add(mesh["object"])
    terrain = terrains[0]
    if terrain["terrain_map"] is not None:
        ref = terrain["terrain_map"]
        texture_deps.setdefault(ref["package"], set()).add(ref["object"])
    for layer in terrain["layers"]:
        for key in ("texture", "alpha_map"):
            ref = layer.get(key)
            if ref is None:
                continue
            texture_deps.setdefault(ref["package"], set()).add(ref["object"])

    result = {
        "schema": SCHEMA_VERSION,
        "map": package.package_name,
        "source": {
            "path": os.path.abspath(path),
            "sha256": _sha256_file(path),
            "size": os.path.getsize(path),
        },
        "package": {
            "version": package.version,
            "licensee": package.licensee,
            "names": package.name_count,
            "imports": package.import_count,
            "exports": package.export_count,
        },
        "stats": {
            "actors": len(actors),
            "static_mesh_actors": class_counts["StaticMeshActor"],
            "player_starts": class_counts["PlayerStart"],
            "terrain_infos": class_counts["TerrainInfo"],
            "legacy_terrain_sectors": class_counts["TerrainSector"],
            "unique_meshes": sum(len(v) for v in mesh_deps.values()),
            "mesh_packages": len(mesh_deps),
            "texture_packages": len(texture_deps),
            "terrain_layers": terrain["layer_count"],
            "terrain_valid_layers": terrain["valid_layer_count"],
            "deleted_static_mesh_actors": sum(
                1 for a in actors if a["class"] == "StaticMeshActor" and a["deleted"]
            ),
            "placeable_static_mesh_actors": sum(
                1
                for a in actors
                if a["class"] == "StaticMeshActor" and not a["deleted"] and a["mesh"] is not None
            ),
        },
        "class_counts": dict(sorted(class_counts.items())),
        "actors": actors,
        "terrain": terrain,
        "dependencies": {
            "meshes": {name: sorted(objects) for name, objects in sorted(mesh_deps.items())},
            "textures": {
                name: sorted(objects) for name, objects in sorted(texture_deps.items())
            },
        },
    }
    return result
