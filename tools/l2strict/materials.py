"""Resolve StaticMesh surface materials and shader diffuse textures."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .errors import AssetError, PackageError
from .package import Package, PackageSet, ResolvedRef
from .properties import read_object

MATERIAL_CLASSES = {
    "Shader",
    "Combiner",
    "FinalBlend",
    "TexEnvMap",
    "TexOscillator",
    "TexPanner",
    "TexRotator",
    "FadeColor",
    "Modifier",
}

# Ordered property names used to find the visible diffuse input of a material.
MATERIAL_SOURCE_PROPERTIES = (
    "Diffuse",
    "Material",
    "Material1",
    "Material2",
)


def _ref_dict(resolved: ResolvedRef, package_name: str | None = None) -> dict:
    return {
        "package": package_name or resolved.package,
        "owner": resolved.package,
        "object": resolved.object,
        "class": resolved.class_name,
        "kind": resolved.kind,
        "outer_chain": resolved.outer_chain,
        "raw": resolved.ref,
    }


def mesh_material_refs(
    package: Package,
    object_names: Iterable[str],
) -> dict[str, list[dict | None]]:
    """Return ``{mesh_name: [material_ref_or_null, ...]}``."""
    wanted = set(object_names)
    result: dict[str, list[dict | None]] = {}
    for index in range(package.export_count):
        if package.class_name_of_export(index) != "StaticMesh":
            continue
        name = package.name(package.exports[index].object_name)
        if name not in wanted:
            continue
        data = package.export_data(index)
        parsed = read_object(
            data,
            package,
            context=f"{package.package_name}:{name}",
            has_stack=False,
        )
        materials = parsed.props.values.get("Materials")
        if materials is None:
            raise AssetError(f"{package.package_name}:{name}: Materials array is missing")
        if not isinstance(materials, list):
            raise AssetError(f"{package.package_name}:{name}: Materials is not an array")
        surface_refs: list[dict | None] = []
        for surface, element in enumerate(materials):
            if not isinstance(element, dict):
                raise AssetError(
                    f"{package.package_name}:{name}: surface {surface} is not a struct"
                )
            ref = element.get("Material", 0)
            if ref == 0:
                surface_refs.append(None)
                continue
            if not isinstance(ref, int):
                raise AssetError(
                    f"{package.package_name}:{name}: surface {surface} has invalid "
                    f"Material reference {ref!r}"
                )
            resolved = package.resolve_ref(ref)
            if resolved is None:
                surface_refs.append(None)
                continue
            surface_refs.append(_ref_dict(resolved))
        result[name] = surface_refs
    missing = wanted - result.keys()
    if missing:
        raise AssetError(
            f"{package.package_name}: missing StaticMesh object(s): {sorted(missing)}"
        )
    return result


def _object_properties(
    pool: PackageSet, package: Package, ref: dict
) -> tuple[Package, int, dict[str, Any]]:
    raw_ref = int(ref.get("raw", 0))
    if raw_ref == 0:
        raise AssetError(f"null material reference: {ref!r}")
    resolved, owner, export_index = pool.resolve(package, raw_ref)
    if owner is None or export_index is None:
        raise PackageError(f"cannot locate material object: {ref!r}")
    data = owner.export_data(export_index)
    parsed = read_object(
        data,
        owner,
        context=f"{owner.package_name}:{resolved.object}",
        has_stack=False,
    )
    return owner, export_index, parsed.props.values


def resolve_material_texture(
    pool: PackageSet,
    source_package: Package,
    ref: dict | None,
    *,
    depth: int = 0,
) -> tuple[dict | None, list[dict]]:
    """Resolve one material reference to its diffuse texture reference.

    Returns ``(texture_ref_or_none, material_chain)``.  ``material_chain`` lists
    every material object visited, which is useful for diagnostics and staging.
    """
    if ref is None:
        return None, []
    if depth > 8:
        raise AssetError(f"material chain too deep at {ref!r}")

    raw_ref = int(ref.get("raw", 0))
    if raw_ref == 0:
        return None, []
    resolved, owner_package, export_index = pool.resolve(source_package, raw_ref)
    if owner_package is None or export_index is None:
        raise PackageError(f"cannot locate material object: {ref!r}")
    chain = [_ref_dict(resolved, owner_package.package_name)]
    if resolved.class_name == "Texture":
        return chain[0], chain

    if resolved.class_name not in MATERIAL_CLASSES:
        # Unknown material classes are preserved but have no texture mapping.
        return None, chain

    data = owner_package.export_data(export_index)
    parsed = read_object(
        data,
        owner_package,
        context=f"{owner_package.package_name}:{resolved.object}",
        has_stack=False,
    )
    values = parsed.props.values
    for prop_name in MATERIAL_SOURCE_PROPERTIES:
        child_raw = values.get(prop_name, 0)
        if child_raw in (None, 0):
            continue
        if not isinstance(child_raw, int):
            raise AssetError(
                f"{owner_package.package_name}:{resolved.object}: {prop_name} is not "
                f"an object reference ({child_raw!r})"
            )
        child_resolved = owner_package.resolve_ref(child_raw)
        if child_resolved is None:
            continue
        child_ref = _ref_dict(child_resolved, owner_package.package_name)
        texture, child_chain = resolve_material_texture(
            pool, owner_package, child_ref, depth=depth + 1
        )
        if texture is not None:
            return texture, chain + child_chain
    return None, chain


def resolve_map_materials(
    map_data: dict,
    pool: PackageSet,
    *,
    mesh_packages: dict[str, set[str]] | None = None,
) -> dict:
    """Resolve every used mesh surface to a diffuse texture.

    ``pool`` must already contain every mesh and material package referenced by
    the map.  The result also records the material packages that had to be
    staged and every texture package/object used by the resolved materials.
    """
    if mesh_packages is None:
        mesh_packages = {
            name: set(objects)
            for name, objects in map_data["dependencies"]["meshes"].items()
        }

    meshes: dict[str, dict[str, list[dict | None]]] = {}
    material_packages: dict[str, set[str]] = {}
    texture_packages: dict[str, set[str]] = {}
    unresolved: list[str] = []

    for package_name in sorted(mesh_packages):
        package = pool.require(package_name)
        refs = mesh_material_refs(package, mesh_packages[package_name])
        meshes[package_name] = {}
        for mesh_name, surfaces in refs.items():
            resolved_surfaces: list[dict | None] = []
            for surface_index, surface in enumerate(surfaces):
                if surface is None:
                    resolved_surfaces.append(None)
                    continue
                material_packages.setdefault(surface["package"], set()).add(
                    surface["object"]
                )
                texture, chain = resolve_material_texture(pool, package, surface)
                for item in chain:
                    material_packages.setdefault(item["package"], set()).add(
                        item["object"]
                    )
                if texture is None:
                    unresolved.append(
                        f"{package_name}:{mesh_name}:surface{surface_index}:"
                        f"{surface['package']}:{surface['object']}"
                    )
                    resolved_surfaces.append(None)
                    continue
                texture_packages.setdefault(texture["package"], set()).add(
                    texture["object"]
                )
                resolved_surfaces.append(texture)
            meshes[package_name][mesh_name] = resolved_surfaces

    return {
        "schema": 1,
        "meshes": {
            package: {
                mesh: surfaces
                for mesh, surfaces in sorted(objects.items())
            }
            for package, objects in sorted(meshes.items())
        },
        "material_packages": {
            name: sorted(objects) for name, objects in sorted(material_packages.items())
        },
        "texture_packages": {
            name: sorted(objects) for name, objects in sorted(texture_packages.items())
        },
        "unresolved": sorted(set(unresolved)),
    }
