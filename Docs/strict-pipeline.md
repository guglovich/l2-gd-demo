# Strict pipeline (`tools/l2strict`)

`tools/l2strict` is the current, reproducible map/mesh/texture pipeline for
the Dark Elf Village tile `20_18`. It replaces the older `tools/l2_*.py`
scripts, which remain in the repository only for comparison until `20_18`
has passed verification.

## Commands

Run these from the project root (`Projects/Lineage 2 Godot/`).

Everything for one tile (staging, extraction, terrain, assets):

```bash
python3 -m tools.l2strict build \
  --source-root /Games/ElmoreX3 \
  --work-dir tmp/l2/20_18 \
  --map 20_18 \
  --neighbor 21_18 --neighbor 20_19 --neighbor 21_19 \
  --assets-dir assets/maps/20_18 \
  --expect StaticMeshActor=799 \
  --expect PlayerStart=5 \
  --expect TerrainInfo=1 \
  --expect TerrainSector=256
```

Verify the finished export:

```bash
python3 -m tools.l2strict verify \
  --work-dir tmp/l2/20_18 \
  --assets-dir assets/maps/20_18 \
  --map 20_18
```

Inspect a package or extract a map without exporting assets:

```bash
python3 -m tools.l2strict probe tmp/l2/20_18/decrypted/MAPS/20_18.unr --classes
python3 -m tools.l2strict extract tmp/l2/20_18/decrypted/MAPS/20_18.unr --out tmp/l2/20_18/map.json
```

## Output layout

```
tmp/l2/20_18/
  decrypted/                only the packages this map needs
    manifest.json          source/output paths, hashes, crypt version, XOR key
    MAPS/20_18.unr
    StaticMeshes/...
    Textures/...
  map.json                 strict actor/terrain/dependency export
  materials.json           mesh package -> mesh -> per-surface texture refs
  terrain/
    terrain.json           exact terrain metadata and hashes
    height_source_g16.raw  256x256 u16 heightmap
    height_world_f32.raw   257x257 absolute game-Z heights
    surface_present_u8.raw 256x256, 1=surface, 0=hole
    edge_turn_u8.raw       256x256 triangle diagonal selection
  umodel/                  raw UModel exports before staging
  umodel.log               one log entry per UModel invocation

assets/maps/20_18/
  map.json                 copied from tmp/l2/20_18
  materials.json
  asset_map.json           import package::object -> glTF + surface indices
  terrain/                 terrain JSON + raw files
  meshes/<pkg>/StaticMesh/<obj>.gltf (+ .bin)
  textures/<pkg>/Texture/<obj>.png
```

## Strict gates

`build` and `verify` fail if any of the following is not exact:

* Package tables are bounds-checked; invalid name/import/export indices abort.
* Every target actor consumes its serial object exactly, with zero trailing
  bytes.
* The map contains exactly the expected class counts
  (799 `StaticMeshActor`, 5 `PlayerStart`, 1 `TerrainInfo`,
  256 legacy `TerrainSector`).
* The terrain export has 256x256 source samples, a 257x257 world grid,
  origin `(0, 0)`, extent `32768x32768`, zero clamped border samples,
  61364 visible quads, 4172 hole quads, and 4063 edge-turn quads.
* All mesh materials resolve to textures; `materials.json` has no unresolved
  entries.
* Exactly 129 glTF meshes are exported, sanitized, and present in
  `asset_map.json`.
* Exactly 211 unique texture PNGs are exported and present.
* Every actor mesh used by a non-deleted, non-hidden actor has an
  `asset_map.json` entry.
* Staged file hashes match `manifest.json`, `map.json`, and `terrain.json`.

The same parser also extracts legacy `18_20` with zero errors
(2618 actors, 2613 `StaticMeshActor`, 5 `PlayerStart`, 1 `TerrainInfo`,
256 legacy `TerrainSector`), so the strict reader is not specific to `20_18`.

## Coordinates and transforms

* UModel exports glTF in meters, with Unreal's Y and Z already swapped.
* Runtime mapping is `godot = (ue_x, ue_z, ue_y) * 0.01`.
* Actor rotation uses the exact Unreal rotator matrix from l2mapper, not
  Godot Euler angles:
  ```
  Basis(
      Vector3(cp*cy, sp, cp*sy) * godot_scale_x,
      Vector3(-(cr*sp*cy + sr*sy), cr*cp, cy*sr - cr*sp*sy) * godot_scale_y,
      Vector3(sr*sp*cy - cr*sy, -sr*cp, sr*sp*sy + cr*cy) * godot_scale_z
  )
  ```
* Scale columns are `(DrawScale3D.x, DrawScale3D.z, DrawScale3D.y) * DrawScale`.
* `PrePivot` is applied in local space before scale and rotation:
  `origin = location - basis * pre_pivot`.

## Terrain

`terrain.py` derives everything from `TerrainInfo`:

* `origin.xy = Location.xy - (width/2*TerrainScale.x, height/2*TerrainScale.y)`
* `origin.z = Location.z - 32768 * TerrainScale.z / 256`
* `height = raw * TerrainScale.z / 256 + origin.z`
* Border vertices are sampled from the real neighbor heightmaps
  (`21_18`, `20_19`, `21_19`) using their own origins, scales, and
  `EdgeTurnBitmap`.
* `QuadVisibilityBitmap` removes hole quads.
* `EdgeTurnBitmap` selects the triangle diagonal in every remaining quad.
* The mesh is 257x257 vertices; the runtime builds it from
  `height_world_f32.raw`, `surface_present_u8.raw`, and `edge_turn_u8.raw`.

## Terrain holes and hole-filling colliders

- `surface_present_u8.raw` is the `QuadVisibilityBitmap` hole mask:
  `0` = hole (no valid terrain surface), `1` = surface. Hole cells hold
  placeholder raw 2511 and must not be rendered, collided, or sampled.
- The terrain mesh skips hole quads; terrain trimesh collision excludes them.
- The Dark Elf Village hole is a legitimate cutout filled by static meshes
  (`O_DE_MT_Out/In/Btm`, `O_De_03`, `O_DE_Btm*` …). Any static mesh whose
  world AABB covers a hole cell gets a trimesh collider, cached per unique
  mesh key in `_trimesh_cache` and shared across instances.
- Player spawn is hole-aware: if the `PlayerStart` cell has no surface, the
  stored `PlayerStart` Z plus 0.9 m clearance is used instead of sampling
  the heightfield.

## Terrain layers

`20_18` has eight valid color layers plus one empty terminator slot. The
shader blends them in slot order over a neutral gray base, matching the
public l2mapconv renderer:

```
su = 2 * layer_scale.x / (128 * 128 * uscale)
sv = 2 * layer_scale.y / (128 * 128 * vscale)
uv = (origin + tile_uv * extent) * (su, sv) + uv_offset
```

Masks use tile UV `0..1`.

## Material and asset mapping

* `materials.json` maps
  `mesh import package -> mesh object -> [texture ref per surface]`.
* `asset_map.json` maps `import package:mesh object` to:
  * the actual staged package name (filenames are case-sensitive on Linux),
  * the `res://` glTF path,
  * the original `StaticMesh` surface index for every surviving glTF
    primitive, so zero-count primitive removal cannot shift materials.
* Mesh surface textures are loaded from
  `assets/maps/20_18/textures/<canonical package>/Texture/<object>.png`.
