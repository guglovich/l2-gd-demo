# Lineage 2 Godot — Dark Elf Village (`20_18`)

Godot 4.7 fork of Lineage 2 (Interlude-era client data). One location —
Dark Elf Village, map `MAPS/20_18.unr` — one character (Dark Elf female,
m013 set), no server, no mobs. Runs natively on Linux.

## Status

- **Strict pipeline (`tools/l2strict`) works end to end**: stage → decrypt →
  strict extract → material closure → exact terrain → UModel export →
  sanitized glTF/PNG → per-map Godot assets.
- **World renders**: 795 placeable static meshes with original textures,
  exact actor transforms, a 257×257 data-driven terrain mesh with the real
  heightmap, visibility holes, edge-turn diagonals, and all eight terrain
  color layers.
- **Character** stands in T-pose at the village spawn; third-person camera,
  WASD + mouse orbit, Shift to run, exact terrain-height following.
- **Verified**: `python3 -m tools.l2strict verify ...` passes all gates
  (actor counts, terrain counts/hashes, 129 meshes, 211 textures, staged
  hashes, no unresolved materials).
- **Not done yet**: walk/run/idle animations (PSA exported, converter TODO —
  see `Docs/psa-format.md`), Steam Audio plugin, export presets.

Legacy `18_20` assets and the old `tools/l2_*.py` scripts remain untouched
for comparison/rollback; the current world does not use them.

## Run

```bash
godot --path .          # or: godot --path . --rendering-driver opengl3
```

Debug switches (optional env vars):
- `L2_DEBUG_CAM=1` — top-down camera; `L2_DEBUG_CAM=down` — 6 m straight down.
- `L2_BRIGHT=1` — bright verification lighting (default placeholder
  lighting untouched; final lighting is a separate task).
- `L2_UNSHADED=1` — render raw albedo without lighting (verifies texture
  layout).
- `L2_SPAWN="x,y,z"` — override spawn point, raw L2 units.
- `L2_SCREENSHOT=/abs/dir` — write `shot1.png`/`shot2.png`, then quits.

Example: `L2_BRIGHT=1 godot --path .`

## Rebuild everything

The pipeline is client-agnostic: `--source-root` is any UE2.5-era
Lineage 2 client directory — the decrypt/extract stage finds the packages
inside it.

```bash
python3 -m tools.l2strict build \
  --source-root /path/to/l2-client \
  --work-dir tmp/l2/20_18 \
  --map 20_18 \
  --neighbor 21_18 --neighbor 20_19 --neighbor 21_19 \
  --assets-dir assets/maps/20_18 \
  --expect StaticMeshActor=799 \
  --expect PlayerStart=5 \
  --expect TerrainInfo=1 \
  --expect TerrainSector=256

python3 -m tools.l2strict verify \
  --work-dir tmp/l2/20_18 \
  --assets-dir assets/maps/20_18 \
  --map 20_18

godot --headless --import --path .
```

See `Docs/strict-pipeline.md` for the full data layout, coordinate rules,
and verification gates.

## Layout

```
assets/maps/20_18/       current per-map assets (JSON, raw terrain, glTF, PNG)
assets/character/        FDarkElf_m013_{u,l,b,g}.gltf
assets/meshes/           legacy 18_20 meshes (unused by the current world)
assets/textures/         legacy 18_20 textures (unused by the current world)
assets/terrain/          legacy 18_20 terrain masks (unused)
scenes/main.tscn         root scene; scripts/world.gd builds everything
scripts/world.gd         map-driven world builder
scripts/player.gd        third-person controller
scripts/terrain.gdshader 8-layer terrain blend
tools/l2strict/          strict pipeline package
tools/l2_*.py            legacy pipeline (kept for comparison)
Docs/                    English documentation; DEVLOG.md is the handoff journal
tmp/l2/20_18/            regenerable strict-pipeline work area
tmp/decrypted/           legacy decrypted packages (regenerable)
```
