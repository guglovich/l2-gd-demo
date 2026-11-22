"""Strict verification of one exported map and its Godot assets."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .errors import VerificationError


def _load_json(path: str) -> dict:
    if not os.path.isfile(path):
        raise VerificationError(f"missing JSON file: {path}")
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise VerificationError(f"invalid JSON object: {path}")
    return data


def _sha256_file(path: str) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _texture_path(assets_dir: str, ref: dict) -> str:
    return os.path.join(
        assets_dir,
        "textures",
        str(ref["package"]),
        "Texture",
        f"{ref['object']}.png",
    )


def verify_map(
    *,
    work_dir: str,
    assets_dir: str,
    map_name: str,
) -> dict:
    errors: list[str] = []
    checks: list[str] = []

    map_path = os.path.join(work_dir, "map.json")
    materials_path = os.path.join(work_dir, "materials.json")
    terrain_json_path = os.path.join(work_dir, "terrain", "terrain.json")
    manifest_path = os.path.join(work_dir, "decrypted", "manifest.json")

    map_data = _load_json(map_path)
    materials = _load_json(materials_path)
    terrain = _load_json(terrain_json_path)
    manifest = _load_json(manifest_path) if os.path.isfile(manifest_path) else {}

    asset_map_path = os.path.join(assets_dir, "asset_map.json")
    asset_map = _load_json(asset_map_path)

    # DEVLOG-107: per-map gates (the pipeline is multi-tile now — 20_17
    # joined 20_18; each tile carries its own verified counts)
    expected_stats = {
        "20_18": {
            "actors": 938,
            "static_mesh_actors": 799,
            "player_starts": 5,
            "terrain_infos": 1,
            "legacy_terrain_sectors": 256,
            "unique_meshes": 129,
            "mesh_packages": 9,
            "texture_packages": 3,
            "terrain_layers": 9,
            "terrain_valid_layers": 8,
            "deleted_static_mesh_actors": 4,
            "placeable_static_mesh_actors": 795,
        },
        "20_17": {
            "actors": 1127,
            "static_mesh_actors": 1109,
            "player_starts": 8,
            "terrain_infos": 1,
            "legacy_terrain_sectors": 256,
            "unique_meshes": 78,
            "mesh_packages": 5,
            "texture_packages": 3,
            "terrain_layers": 12,
            "terrain_valid_layers": 12,
            "deleted_static_mesh_actors": 0,
            "placeable_static_mesh_actors": 1109,
        },
        "21_18": {
            "actors": 2312,
            "static_mesh_actors": 2309,
            "player_starts": 1,
            "terrain_infos": 1,
            "legacy_terrain_sectors": 256,
            "unique_meshes": 115,
            "mesh_packages": 6,
            "texture_packages": 3,
            "terrain_layers": 10,
            "terrain_valid_layers": 10,
            "deleted_static_mesh_actors": 0,
            "placeable_static_mesh_actors": 2309,
        },
        "19_18": {
            "actors": 3724,
            "static_mesh_actors": 1966,
            "player_starts": 3,
            "terrain_infos": 1,
            "legacy_terrain_sectors": 256,
            "unique_meshes": 90,
            "mesh_packages": 5,
            "texture_packages": 3,
            "terrain_layers": 10,
            "terrain_valid_layers": 9,
            "deleted_static_mesh_actors": 12,
            "placeable_static_mesh_actors": 1954,
        },
        "19_19": {
            "actors": 1513,
            "static_mesh_actors": 1511,
            "player_starts": 1,
            "terrain_infos": 1,
            "legacy_terrain_sectors": 256,
            "unique_meshes": 58,
            "mesh_packages": 5,
            "texture_packages": 3,
            "terrain_layers": 11,
            "terrain_valid_layers": 10,
            "deleted_static_mesh_actors": 0,
            "placeable_static_mesh_actors": 1511,
        },
        "18_19": {
            "actors": 1859,
            "static_mesh_actors": 1683,
            "player_starts": 1,
            "terrain_infos": 1,
            "legacy_terrain_sectors": 256,
            "unique_meshes": 69,
            "mesh_packages": 4,
            "texture_packages": 3,
            "terrain_layers": 8,
            "terrain_valid_layers": 8,
            "deleted_static_mesh_actors": 0,
            "placeable_static_mesh_actors": 1683,
        },
        # DEVLOG-136: the 20_19 control map (the default weather, the
        # comparison against 20_18's terrain lighting)
        "20_19": {
            "actors": 1113,
            "static_mesh_actors": 1112,
            "player_starts": 1,
            "terrain_infos": 1,
            "legacy_terrain_sectors": 256,
            "unique_meshes": 82,
            "mesh_packages": 6,
            "texture_packages": 3,
            "terrain_layers": 10,
            "terrain_valid_layers": 9,
            "deleted_static_mesh_actors": 0,
            "placeable_static_mesh_actors": 1112,
        },
    }.get(map_name)
    if expected_stats is None:
        errors.append(f"no verify gates registered for map {map_name}")
        expected_stats = {}
    for key, expected in expected_stats.items():
        actual = map_data.get("stats", {}).get(key)
        _check(
            actual == expected,
            f"map stat {key}: expected {expected}, got {actual}",
            errors,
        )
        if actual == expected:
            checks.append(f"map stat {key}={actual}")

    _check(
        not materials.get("unresolved", []),
        f"unresolved mesh materials: {materials.get('unresolved', [])[:10]}",
        errors,
    )
    if not materials.get("unresolved", []):
        checks.append("mesh materials resolved")

    expected_terrain_common = {
        "source_height_size": [256, 256],
        "height_world_size": [257, 257],
        "extent_game_xy": [32768.0, 32768.0],
        "clamped_border_samples": 0,
    }
    expected_terrain_by_map = {
        "20_18": {
            "origin_game_xy": [0.0, 0.0],
            "visible_quad_count": 61364,
            "hole_quad_count": 4172,
            "edge_turn_quad_count": 4063,
        },
        "20_17": {
            "origin_game_xy": [0.0, -32768.0],
            "visible_quad_count": 65503,
            "hole_quad_count": 33,
            "edge_turn_quad_count": 5469,
        },
        "21_18": {
            "origin_game_xy": [32768.0, 0.0],
            "visible_quad_count": 65536,
            "hole_quad_count": 0,
            "edge_turn_quad_count": 4855,
        },
        "19_18": {
            "origin_game_xy": [-32768.0, 0.0],
            "visible_quad_count": 65487,
            "hole_quad_count": 49,
            "edge_turn_quad_count": 5667,
        },
        # DEVLOG-113: one border sample is clamped because the client
        # ships NO corner heightmap for the pure-ocean corner tiles
        # (t_20_20 / t_18_20 are absent from Textures/) — the SE corner
        # vertex of 19_19 clamps to the available edge heightmaps. The
        # east/south EDGES sample from the real t_20_19 / t_19_20.
        "19_19": {
            "origin_game_xy": [-32768.0, 32768.0],
            "visible_quad_count": 65511,
            "hole_quad_count": 25,
            "edge_turn_quad_count": 11679,
            "clamped_border_samples": 1,
        },
        # DEVLOG-115: the whole SOUTH edge (256 samples) clamps because
        # the south neighbor 18_20 is a pure-ocean tile with NO terrain
        # data (t_18_20 absent). The east edge samples from the real
        # t_19_19 (the seam measured 0.00); the 6496 hole quads are the
        # tile's own water/cutout mask.
        "18_19": {
            "origin_game_xy": [-65536.0, 32768.0],
            "visible_quad_count": 59040,
            "hole_quad_count": 6496,
            "edge_turn_quad_count": 1932,
            "clamped_border_samples": 256,
        },
        # DEVLOG-136: the 20_19 control map — all five neighbours staged,
        # zero border clamps
        "20_19": {
            "origin_game_xy": [0.0, 32768.0],
            "visible_quad_count": 65536,
            "hole_quad_count": 0,
            "edge_turn_quad_count": 11015,
            "clamped_border_samples": 0,
        },
    }
    expected_terrain = dict(
        expected_terrain_common,
        **expected_terrain_by_map.get(
            map_name,
            {"origin_game_xy": terrain.get("origin_game_xy"),
             "visible_quad_count": terrain.get("visible_quad_count"),
             "hole_quad_count": terrain.get("hole_quad_count"),
             "edge_turn_quad_count": terrain.get("edge_turn_quad_count")},
        ),
    )
    for key, expected in expected_terrain.items():
        actual = terrain.get(key)
        _check(
            actual == expected,
            f"terrain {key}: expected {expected}, got {actual}",
            errors,
        )
        if actual == expected:
            checks.append(f"terrain {key}={actual}")
    # DEVLOG-113: the per-map expected warnings — 19_19 legitimately
    # carries the ocean-corner clamp warnings (t_20_20 / t_18_20 absent).
    expected_warnings = {
        "19_19": [
            "1 terrain border sample(s) clamped to available heightmaps",
            "southeast terrain neighbour unavailable",
        ],
        "18_19": [
            "256 terrain border sample(s) clamped to available heightmaps",
            "south terrain neighbour unavailable",
        ],
    }.get(map_name, [])
    _check(
        sorted(terrain.get("warnings", [])) == sorted(expected_warnings),
        f"terrain warnings: {terrain.get('warnings', [])}",
        errors,
    )

    expected_terrain_files = {
        "height_source_g16": 131072,
        "height_world_f32": 264196,
        "surface_present_u8": 65536,
        "edge_turn_u8": 65536,
    }
    for key, expected_size in expected_terrain_files.items():
        entry = terrain.get("files", {}).get(key)
        _check(entry is not None, f"terrain file metadata missing: {key}", errors)
        if entry is None:
            continue
        path = os.path.join(work_dir, "terrain", os.path.basename(entry["path"]))
        _check(
            os.path.isfile(path),
            f"terrain file missing: {path}",
            errors,
        )
        if not os.path.isfile(path):
            continue
        _check(
            os.path.getsize(path) == expected_size,
            f"terrain file size {key}: expected {expected_size}, got {os.path.getsize(path)}",
            errors,
        )
        actual_hash = _sha256_file(path)
        _check(
            actual_hash == entry["sha256"],
            f"terrain file hash mismatch: {key}",
            errors,
        )
        if actual_hash == entry["sha256"]:
            checks.append(f"terrain hash {key}")

    mesh_count = 0
    texture_refs: set[str] = set()
    gltf_errors = 0
    for mesh_key, info in asset_map.get("meshes", {}).items():
        mesh_count += 1
        gltf_path = os.path.abspath(
            os.path.join(os.getcwd(), info["gltf"].removeprefix("res://"))
        )
        _check(
            os.path.isfile(gltf_path),
            f"missing glTF: {info['gltf']}",
            errors,
        )
        if not os.path.isfile(gltf_path):
            continue
        with open(gltf_path, "r", encoding="utf-8") as fp:
            document = json.load(fp)
        zero_accessors = [
            accessor
            for accessor in document.get("accessors", [])
            if accessor.get("count", 0) == 0
        ]
        gltf_errors += len(zero_accessors)
        _check(
            not zero_accessors,
            f"glTF has zero-count accessors: {mesh_key}",
            errors,
        )
        _check(
            bool(document.get("meshes")),
            f"glTF has no meshes: {mesh_key}",
            errors,
        )
        primitive_indices = info.get("primitive_material_indices", [])
        mesh_count_in_document = len(document.get("meshes", []))
        _check(
            len(primitive_indices) > 0,
            f"glTF has no primitive material indices: {mesh_key}",
            errors,
        )
        _check(
            mesh_count_in_document == 1,
            f"glTF has multiple mesh objects: {mesh_key}",
            errors,
        )

    expected_mesh_count = {
        "20_18": 133,
        "20_17": 78,
        "21_18": 115,
        "19_18": 90,
    }.get(map_name, mesh_count)
    _check(mesh_count == expected_mesh_count,
           f"asset map mesh count: {mesh_count}", errors)
    _check(gltf_errors == 0, f"glTF zero-count accessor total: {gltf_errors}", errors)
    if mesh_count == expected_mesh_count and gltf_errors == 0:
        checks.append("glTF meshes sanitized")

    for package, meshes in materials.get("meshes", {}).items():
        for mesh, surfaces in meshes.items():
            for surface in surfaces:
                if surface is None:
                    continue
                texture_refs.add(f"{surface['package']}:{surface['object']}")
                path = _texture_path(assets_dir, surface)
                _check(
                    os.path.isfile(path),
                    f"missing mesh texture: {package}:{mesh}: {path}",
                    errors,
                )
    for layer in terrain.get("layers", []):
        for key in ("texture", "mask"):
            ref = layer.get(key)
            if ref is None:
                continue
            texture_refs.add(f"{ref['package']}:{ref['object']}")
            path = _texture_path(assets_dir, ref)
            _check(
                os.path.isfile(path),
                f"missing terrain {key}: {path}",
                errors,
            )
    texture_count = len(texture_refs)
    expected_texture_count = {
        "20_18": 211,
        "20_17": 131,
        "21_18": 118,
        "19_18": 147,
    }.get(map_name, texture_count)
    _check(texture_count == expected_texture_count,
           f"texture reference count: {texture_count}", errors)
    if texture_count == expected_texture_count:
        checks.append("texture references complete")

    actor_meshes = set()
    for actor in map_data.get("actors", []):
        if actor.get("deleted") or actor.get("hidden"):
            continue
        mesh = actor.get("mesh")
        if mesh is None:
            continue
        actor_meshes.add(f"{mesh['package']}:{mesh['object']}")
    missing_meshes = sorted(actor_meshes - set(asset_map.get("meshes", {})))
    _check(
        not missing_meshes,
        f"actor meshes missing from asset map: {missing_meshes[:10]}",
        errors,
    )
    if not missing_meshes:
        checks.append("actor meshes complete")

    manifest_files = {
        Path(entry["source"]).stem.casefold(): entry
        for entry in manifest.get("files", [])
    }
    map_entry = manifest_files.get(map_name.casefold())
    _check(
        map_entry is not None,
        f"map missing from staging manifest: {map_name}",
        errors,
    )
    if map_entry is not None:
        actual_hash = _sha256_file(map_entry["output"])
        _check(
            actual_hash == map_entry["output_sha256"],
            "staged map hash differs from manifest",
            errors,
        )
        _check(
            map_data.get("source", {}).get("sha256") == map_entry["output_sha256"],
            "map.json source hash differs from staged map",
            errors,
        )
        if (
            actual_hash == map_entry["output_sha256"]
            and map_data.get("source", {}).get("sha256") == map_entry["output_sha256"]
        ):
            checks.append("staged map hash")

    if errors:
        raise VerificationError(
            f"{map_name}: {len(errors)} verification error(s):\n"
            + "\n".join(f"- {error}" for error in errors)
        )

    return {
        "map": map_name,
        "checks": checks,
        "meshes": mesh_count,
        "textures": texture_count,
        "status": "ok",
    }
