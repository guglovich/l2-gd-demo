"""Export selected L2 objects with UModel and stage them for Godot."""

from __future__ import annotations

import json
import os
import shutil
import subprocess

from .errors import AssetError
from .package import PackageSet


def _res_path(path: str) -> str:
    """Convert a project-relative file path to a Godot ``res://`` path."""
    relative = os.path.relpath(os.path.abspath(path), os.getcwd())
    relative = relative.replace(os.sep, "/")
    return "res://" + relative


def _umodel(
    staged_root: str,
    out_root: str,
    log_path: str,
    source_relative: str,
    object_name: str,
    class_name: str,
    *,
    mesh: bool,
) -> None:
    command = [
        "umodel",
        f"-path={staged_root}",
        "-game=l2",
        "-export",
    ]
    if mesh:
        command.append("-gltf")
    else:
        command.append("-png")
    command.extend(
        [
            f"-out={out_root}",
            source_relative,
            object_name,
            class_name,
        ]
    )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as log:
        log.write("\n### " + " ".join(command) + "\n")
        log.flush()
        result = subprocess.run(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode != 0:
        raise AssetError(
            f"umodel failed with code {result.returncode}: {object_name} "
            f"({source_relative})"
        )


def _sanitize_gltf(path: str, context: str) -> tuple[bool, list[int]]:
    """Remove zero-count accessors/primitives.

    Returns ``(mesh_is_valid, primitive_material_indices)``.  The material
    indices are the original StaticMesh surface indices and survive primitive
    removal, so the runtime can map Godot surfaces back to L2 materials.
    """
    with open(path, "r", encoding="utf-8") as fp:
        document = json.load(fp)

    accessors = document.get("accessors", [])
    keep = [i for i, accessor in enumerate(accessors) if accessor.get("count", 0) > 0]
    keep_set = set(keep)
    remap = {old: new for new, old in enumerate(keep)}
    if len(keep) != len(accessors):
        document["accessors"] = [accessors[i] for i in keep]

    meshes = document.get("meshes", [])
    kept_meshes = []
    for mesh in meshes:
        primitives = []
        for primitive in mesh.get("primitives", []):
            indices = primitive.get("indices")
            if indices is not None and indices not in keep_set:
                continue
            attributes = primitive.get("attributes", {})
            if any(accessor not in keep_set for accessor in attributes.values()):
                continue
            if indices is not None:
                primitive["indices"] = remap[indices]
            primitive["attributes"] = {
                name: remap[accessor] for name, accessor in attributes.items()
            }
            primitives.append(primitive)
        if not primitives:
            continue
        mesh["primitives"] = primitives
        kept_meshes.append(mesh)
    document["meshes"] = kept_meshes
    if not kept_meshes:
        return False, []

    # Nodes reference meshes by index; rebuild that mapping when empty meshes
    # were removed.
    mesh_ids = {id(mesh): i for i, mesh in enumerate(kept_meshes)}
    old_ids = {id(mesh): i for i, mesh in enumerate(meshes)}
    for node in document.get("nodes", []):
        if "mesh" not in node:
            continue
        old_index = node["mesh"]
        if old_index >= len(meshes):
            raise AssetError(f"{context}: node references invalid mesh {old_index}")
        if id(meshes[old_index]) not in mesh_ids:
            node.pop("mesh", None)
            continue
        node["mesh"] = mesh_ids[id(meshes[old_index])]

    buffers = document.get("buffers", [])
    if not buffers:
        raise AssetError(f"{context}: glTF has no buffers")
    uri = buffers[0].get("uri")
    if not uri:
        raise AssetError(f"{context}: glTF buffer has no URI")
    bin_path = os.path.join(os.path.dirname(path), os.path.basename(uri))
    if not os.path.isfile(bin_path):
        raise AssetError(f"{context}: missing glTF buffer {bin_path}")

    primitive_material_indices: list[int] = []
    for mesh in kept_meshes:
        for primitive in mesh.get("primitives", []):
            primitive_material_indices.append(int(primitive.get("material", -1)))

    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as fp:
        json.dump(document, fp, indent=2)
        fp.write("\n")
    os.replace(temp_path, path)
    return True, primitive_material_indices


def _copy_pair(source_gltf: str, destination_dir: str) -> tuple[str, str]:
    os.makedirs(destination_dir, exist_ok=True)
    document = json.load(open(source_gltf, "r", encoding="utf-8"))
    uri = document["buffers"][0]["uri"]
    source_bin = os.path.join(os.path.dirname(source_gltf), os.path.basename(uri))
    destination_gltf = os.path.join(destination_dir, os.path.basename(source_gltf))
    destination_bin = os.path.join(destination_dir, os.path.basename(source_bin))
    shutil.copyfile(source_gltf, destination_gltf)
    shutil.copyfile(source_bin, destination_bin)
    return destination_gltf, destination_bin


def export_assets(
    *,
    work_dir: str,
    assets_dir: str,
    map_data: dict,
    materials: dict,
    terrain: dict,
    pool: PackageSet,
) -> dict:
    """Export used meshes/textures and copy them plus terrain data to Godot."""
    staged_root = os.path.abspath(os.path.join(work_dir, "decrypted"))
    umodel_root = os.path.abspath(os.path.join(work_dir, "umodel"))
    log_path = os.path.abspath(os.path.join(work_dir, "umodel.log"))
    os.makedirs(umodel_root, exist_ok=True)
    if os.path.exists(log_path):
        os.unlink(log_path)

    mesh_outputs: dict[str, dict] = {}
    mesh_asset_map: dict[str, dict] = {}
    for package_name, meshes in materials["meshes"].items():
        package = pool.get(package_name)
        if package is None or package.path is None:
            raise AssetError(f"mesh package is not staged: {package_name}")
        relative = os.path.relpath(package.path, staged_root)
        for object_name in meshes:
            _umodel(
                staged_root,
                umodel_root,
                log_path,
                relative,
                object_name,
                "StaticMesh",
                mesh=True,
            )
            source = os.path.join(
                umodel_root, package.package_name, "StaticMesh", f"{object_name}.gltf"
            )
            if not os.path.isfile(source):
                raise AssetError(f"umodel did not create {source}")
            valid, primitive_material_indices = _sanitize_gltf(
                source, f"{package_name}:{object_name}"
            )
            if not valid:
                raise AssetError(f"{package_name}:{object_name}: glTF mesh is empty")
            destination = os.path.join(
                assets_dir, "meshes", package.package_name, "StaticMesh"
            )
            gltf_path, bin_path = _copy_pair(source, destination)
            mesh_key = f"{package_name}:{object_name}"
            mesh_outputs[mesh_key] = {
                "gltf": gltf_path,
                "bin": bin_path,
                "primitive_material_indices": primitive_material_indices,
            }
            mesh_asset_map[mesh_key] = {
                "package": package.package_name,
                "gltf": _res_path(gltf_path),
                "primitive_material_indices": primitive_material_indices,
            }

    texture_objects: dict[str, set[str]] = {}
    for package_name, objects in materials["texture_packages"].items():
        texture_objects.setdefault(package_name, set()).update(objects)
    for layer in terrain["layers"]:
        for key in ("texture", "mask"):
            ref = layer.get(key)
            if ref is not None:
                texture_objects.setdefault(ref["package"], set()).add(ref["object"])

    texture_outputs: dict[str, dict] = {}
    for package_name in sorted(texture_objects):
        package = pool.get(package_name)
        if package is None or package.path is None:
            raise AssetError(f"texture package is not staged: {package_name}")
        relative = os.path.relpath(package.path, staged_root)
        for object_name in sorted(texture_objects[package_name]):
            _umodel(
                staged_root,
                umodel_root,
                log_path,
                relative,
                object_name,
                "Texture",
                mesh=False,
            )
            source = os.path.join(
                umodel_root, package.package_name, "Texture", f"{object_name}.png"
            )
            if not os.path.isfile(source):
                raise AssetError(f"umodel did not create {source}")
            destination_dir = os.path.join(
                assets_dir, "textures", package.package_name, "Texture"
            )
            os.makedirs(destination_dir, exist_ok=True)
            destination = os.path.join(destination_dir, f"{object_name}.png")
            shutil.copyfile(source, destination)
            texture_outputs[f"{package.package_name}:{object_name}"] = {
                "png": destination
            }

    for name in ("map.json", "materials.json"):
        source = os.path.join(work_dir, name)
        if not os.path.isfile(source):
            raise AssetError(f"missing pipeline data file: {source}")
        shutil.copyfile(source, os.path.join(assets_dir, name))

    terrain_source = os.path.join(work_dir, "terrain")
    terrain_destination = os.path.join(assets_dir, "terrain")
    os.makedirs(terrain_destination, exist_ok=True)
    for entry in os.listdir(terrain_source):
        source = os.path.join(terrain_source, entry)
        if os.path.isfile(source):
            shutil.copyfile(source, os.path.join(terrain_destination, entry))

    asset_map = {
        "schema": 1,
        "map": map_data["map"],
        "meshes": dict(sorted(mesh_asset_map.items())),
    }
    with open(os.path.join(assets_dir, "asset_map.json"), "w", encoding="utf-8") as fp:
        json.dump(asset_map, fp, indent=2)
        fp.write("\n")

    summary = {
        "schema": 1,
        "map": map_data["map"],
        "meshes": len(mesh_outputs),
        "textures": len(texture_outputs),
        "terrain_files": sorted(os.listdir(terrain_destination)),
        "umodel_log": log_path,
    }
    with open(os.path.join(assets_dir, "assets_summary.json"), "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)
        fp.write("\n")
    return {
        "summary": summary,
        "meshes": mesh_outputs,
        "textures": texture_outputs,
        "assets_dir": os.path.abspath(assets_dir),
    }
