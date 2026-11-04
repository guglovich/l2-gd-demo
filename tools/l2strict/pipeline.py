"""End-to-end data stages: stage, extract, and resolve one map."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .errors import StageError
from .extract import extract_map
from .materials import mesh_material_refs, resolve_map_materials
from .package import PackageSet
from .stage import Stager
from .terrain import build_terrain


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
        fp.write("\n")


def _staged_packages(stager: Stager) -> set[str]:
    return set(stager.entries)


def build_map_data(
    *,
    source_root: str,
    work_dir: str,
    map_name: str,
    neighbors: tuple[str, ...] = (),
    expected_counts: dict[str, int] | None = None,
) -> dict:
    """Stage a map and write strict ``map.json`` and ``materials.json``.

    The working directory layout is::

        <work_dir>/decrypted/{MAPS,StaticMeshes,Textures}/...
        <work_dir>/manifest.json
        <work_dir>/map.json
        <work_dir>/materials.json
    """
    stager = Stager(source_root, os.path.join(work_dir, "decrypted"))
    map_output = stager.stage(map_name, category="MAPS")
    map_data = extract_map(map_output, expected_counts=expected_counts)
    _write_json(os.path.join(work_dir, "map.json"), map_data)

    stager.stage_many(
        map_data["dependencies"]["meshes"].keys(), category="StaticMeshes"
    )
    stager.stage_many(
        map_data["dependencies"]["textures"].keys(), category="Textures"
    )
    for neighbor in neighbors:
        stager.stage(neighbor, category="MAPS")
        stager.stage(f"t_{neighbor}", category="Textures")

    decrypted = stager.destination_root
    pool = PackageSet()
    pool.add_directory(decrypted, ("StaticMeshes", "Textures"))

    # Material objects named by mesh surfaces must be staged before shader
    # diffuse references can be resolved.
    material_requests: set[str] = set()
    for package_name, objects in map_data["dependencies"]["meshes"].items():
        package = pool.require(package_name)
        refs = mesh_material_refs(package, objects)
        for surfaces in refs.values():
            for surface in surfaces:
                if surface is not None:
                    material_requests.add(surface["package"])
    stager.stage_many(sorted(material_requests), category="Textures")

    materials = None
    for _ in range(6):
        pool = PackageSet()
        pool.add_directory(decrypted, ("StaticMeshes", "Textures"))
        materials = resolve_map_materials(map_data, pool)
        staged = _staged_packages(stager)
        missing = {
            name
            for name in materials["texture_packages"]
            if Path(name).stem.casefold() not in staged
        }
        if not missing:
            break
        stager.stage_many(sorted(missing), category="Textures")
    else:
        raise StageError("material dependency closure did not converge")

    if materials is None or materials["unresolved"]:
        raise StageError(
            "unresolved mesh materials: "
            + ", ".join((materials or {}).get("unresolved", [])[:20])
        )

    _write_json(os.path.join(work_dir, "materials.json"), materials)
    stager.save_manifest()

    return {
        "map": map_data,
        "materials": materials,
        "manifest": stager.manifest_path,
        "work_dir": os.path.abspath(work_dir),
    }


def build_map(
    *,
    source_root: str,
    work_dir: str,
    map_name: str,
    neighbors: tuple[str, ...] = (),
    expected_counts: dict[str, int] | None = None,
    assets_dir: str | None = None,
) -> dict:
    """Run data, terrain, and optional asset-export stages for one map."""
    data = build_map_data(
        source_root=source_root,
        work_dir=work_dir,
        map_name=map_name,
        neighbors=neighbors,
        expected_counts=expected_counts,
    )
    pool = PackageSet()
    pool.add_directory(
        os.path.join(work_dir, "decrypted"), ("MAPS", "StaticMeshes", "Textures")
    )
    terrain = build_terrain(
        work_dir=work_dir,
        map_data=data["map"],
        pool=pool,
        neighbors=tuple(
            (
                name,
                os.path.join(work_dir, "decrypted", "MAPS", f"{name}.unr"),
            )
            for name in neighbors
        ),
    )

    result = {
        "map": data["map"],
        "materials": data["materials"],
        "terrain": terrain,
        "work_dir": data["work_dir"],
        "manifest": data["manifest"],
    }
    if assets_dir is not None:
        from .assets import export_assets

        assets = export_assets(
            work_dir=work_dir,
            assets_dir=assets_dir,
            map_data=data["map"],
            materials=data["materials"],
            terrain=terrain,
            pool=pool,
        )
        result["assets"] = assets
    return result
