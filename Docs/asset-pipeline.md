# Asset pipeline: original client → Godot

> **Legacy reference.** The current pipeline is `tools/l2strict`; see
> `Docs/strict-pipeline.md`. This document describes the older `tools/l2_*.py`
> flow and is kept for comparison.

Source of truth: `/Games/ElmoreX3/` (Interlude-era client, read-only).

## Pipeline stages

```
/Games/ElmoreX3/MAPS/18_20.unr (Ver111)
  │ tools/l2_decrypt.py
  ▼
tmp/decrypted/MAPS/18_20.unr
  │ tools/l2_extract.py  ──▶ tmp/18_20.json      (actors, terrain, deps)
  │ tools/l2_probe.py                       (dep names)
  ▼
decrypt dependency packages → tmp/decrypted/{StaticMeshes,Textures}/
  │ tools/l2_materials.py ──▶ tmp/materials.json (mesh → [surface → texture])
  ▼
UModel exports (tools/export_meshes.sh, export_textures.sh)
  ├── tmp/umodel_export/<Pkg>/StaticMesh/<Obj>.gltf + .bin
  └── tmp/umodel_export/<Pkg>/Texture/<Tex>.png
  ▼
Godot project: assets/… + runtime world build from JSON (GDScript)
```

## Map JSON (tmp/18_20.json)

```jsonc
{
  "terrain": {
    "terrain_map": "18_20", "terrain_map_pkg": "T_18_20",
    "terrain_scale": [128.0, 128.0, 76.0],
    "layers": [ {"texture":"Base","texture_pkg":"T_texture",
                 "alpha_map":"layer0","alpha_pkg":"T_texture",
                 "u_scale":1.0,"v_scale":1.0,"scale":[..]}, ... ]  // 11 layers
  },
  "actors": [ {"class":"StaticMeshActor","name":"StaticMeshActor192",
               "location":[x,y,z], "rotation":[pitch,yaw,roll],
               "draw_scale":1.0, "draw_scale3d":[1,1,1],
               "mesh":{"package":"Oren_tree_S","object":"Oren_Darkelf_tree12"}} ],
  "packages": { "Oren_tree_S": ["Oren_Darkelf_tree12", ...] }
}
```

## Materials JSON (tmp/materials.json)

`{ mesh_pkg: { mesh_obj: [ [tex_pkg, tex_name] | null, ... ] } }`
Array order = surface order of the exported glTF (sections[i] → material i).

## Coordinates and scale

- L2 world: X east, Y north, Z up. 1 unit = 1 cm → Godot scale factor 0.01.
- Godot mapping: `godot.x = l2.x * 0.01; godot.y = l2.z * 0.01;
  godot.z = -l2.y * 0.01` (so L2 north = Godot -Z).
- Rotator units: 65536 = 360°. Yaw is around L2 Z (up): Godot
  `rotation.y = -yaw * TAU / 65536`. Pitch/roll: rarely used on static
  meshes; apply as Godot z/x rotations with sign flips if needed.
- Map 18_20 terrain tile origin: `X0=(18-16)*32768-131072 = -65536`,
  `Y0=(20-10)*32768-131072 = 65536`. Terrain spans 32768×32768 units
  (256×256 vertices, 128 units per quad).
- Terrain height: `world_z = (height_u16 - 32768) * 76 / 256`.
  PlayerStart z=-4682 falls inside the terrain range (-8474..-835) ✓.

## Character

`Animations/DarkElf.ukx` (unencrypted): `SkeletalMesh FDarkElf_m013_*`
(b=boots, g=gloves, l=lower, u=upper — same skeleton), animation set
`MeshAnimation FDarkElf_anim`. Textures in `SysTextures/fdarkelf.utx`.
UModel exports each part as glTF with the full skeleton; in Godot they are
instantiated as siblings under one root (no merging needed for the demo).
Scale: character ~170 units → 1.7 m at 0.01.

## UModel notes

- Must be fed **decrypted** packages from `tmp/decrypted/` with ORIGINAL
  file names (it resolves imports by name; folders StaticMeshes/Textures
  are searched under `-path`).
- `-game=l2` tag; `-export -gltf -png -out=<ABSOLUTE path>`.
- `-out` MUST be absolute (relative → $HOME).
- StaticMesh glTF has dummy materials; real textures come from
  materials.json and are applied in Godot by surface index.
- Animations cannot be exported to glTF from CLI; use default ActorX export
  → `.psa` (see `psa-format.md`).
- Heightmap texture (TEXF_G16) is NOT exported by UModel — extracted by
  `tools/l2_heightmap.py` directly from the package.
