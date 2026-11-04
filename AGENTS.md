# Project: Lineage 2 Godot (`Projects/Lineage 2 Godot/`)

Fork of Lineage 2 (Interlude-era client) on Godot 4.7. One location
(Dark Elf Village = `MAPS/20_18.unr`), one character (Dark Elf female),
no server, no mobs. Native Linux target (no Wine), test machine: this Arch box.

## Ground rules for this project

- **Source of truth for handoff is `Docs/DEVLOG.md`** — read it first,
  update it at the end of every session. Docs are in English.
- Original client lives at `/Games/ElmoreX3/` — **read-only**, never modify
  or copy wholesale (9.3 GB). Extract only what is needed.
- `tmp/` inside the project holds decrypted packages and UModel exports —
  everything there is regenerable from tools/.
- System packages (godot, umodel, python3-numpy, python3-pillow, java,
  blender) are already installed from Arch repos/AUR — do not vendor them
  into the project.

## Task discipline (HARD RULES, from the user — 2026-11-02)

- **Work ONLY the task stated in the user's prompt.** Drifting to other
  areas (sky, backdrop, other map regions, refactors) is a priority error,
  even if the drift looks useful. If a related defect is noticed, mention
  it in DEVLOG as a pending item and continue the stated task.
- **NO lighting work** until the user opens the lighting stage: do not
  touch sun/ambient/shadows/fog/sky colors of the normal scene. The
  user's stage 1 is textures, maps, geodata only.
- `L2_BRIGHT=1` is a **diagnostic-only flag** (flat white ambient, no
  shadows) whose only purpose is telling "missing geometry" apart from
  "dark texture" on screenshots. It must not alter the normal
  (non-bright) scene in any way.
- **Every visual change must be verified with a screenshot at the player
  spawn point** (`L2_SCREENSHOT=… godot --path .`), not at other
  locations. No task is "done" without that screenshot check.
- The user checks every iteration against the original client screenshot.
  Do not close a task as done without visual proof it matches.
- **The original-client reference screenshot is `Docs/DE_village.png`**
  (the user re-captures it from the live game as needed). Compare every
  visual claim against it — never against memory of the original.
- **Do NOT verify renders by eyeballing screenshots ("OCR").** The agent's
  visual reading of renders has repeatedly been wrong. Use the numeric
  verifier instead: `L2_FLOOR_PROFILE="gx1,gy1,gx2,gy2,steps" godot --path .`
  prints every surface hit (height, normal, owning mesh) along a line.
  Always cross-check suspicious visual findings with floor profiles.

## Tool peculiarities (discovered the hard way)

- L2 `.unr`/`.usx` here are `Lineage2Ver111` (XOR 0xAC after a 28-byte
  UTF-16LE header), `.utx` are `Ver121` (XOR = sum of lowercase filename
  bytes). `.ukx` animations are plain UE packages.
- The L2 package format (ver 123, licensee 28) deviates from stock UE2:
  compact-index FNames in import/export tables, name table indexed from 0
  ("None" is entry 0), compact SerialSize/SerialOffset, TEXTURE/MATERIAL
  objects have a 4-byte prefix before properties (licensee 16–37).
- UModel (`-game=l2`) does NOT read Ver111/121 files — decrypt into
  `tmp/decrypted/` keeping ORIGINAL file names and the StaticMeshes/
  Textures/MAPS folder layout, then point `-path` there.
- UModel `-out=` must be an ABSOLUTE path (relative resolves to $HOME).
- UModel exports glTF **already in meters** (it divides UE cm by 100).
  Do not rescale again.
- UModel cannot export animations to glTF from CLI — export ActorX `.psa`
  instead (`umodel -export`, no `-gltf` flag).
- Some UModel glTF files contain accessors with count=0; Godot refuses the
  whole file. Strip zero-count primitives after export.
- glTF buffers are referenced as `<object>.bin` (no package prefix) inside
  `assets/meshes/` — copy bins under that exact name.
- Godot re-import does not heal `valid=false` .import stamps: delete
  `*.gltf.import` and `.godot/imported/` before re-importing.
- The headless import on this machine: `godot --headless --import --path .`
  (~1–2 min for 190 glTF + 3400 PNG).
- Screenshots for agent verification: `L2_SCREENSHOT=<abs dir> godot --path .`
  (saves shot1/shot2.png then quits); render via `xvfb-run -a … godot …
  --rendering-driver opengl3` (mesa llvmpipe works, vulkan-swrast present
  for Forward+ if needed). `L2_VIEW_YAW` overrides spawn view yaw;
  `L2_BRIGHT=1` (diagnostic only, isolated in `_build_environment()`)
  forces flat white ambient so black regions are recognisable as missing
  geometry rather than shadowed dark textures.
- **MCP servers registered (need ZCode restart to appear in tool list):**
  Craft Anything **0.3.0** (`~/.local/bin/craft-anything-cli mcp --project
  analysis/l2-godot.cany --deep`) and **l2-modding**
  (`tools/l2-modding-mcp/.venv/bin/python -m l2_mcp.server`; 25 tools:
  .utx texture decode/encode, .unr map parse, package scan; it WRITES
  .usx but does NOT read existing StaticMesh geometry). Craft Anything is
  the project RE toolkit: only Essentials tools are listed until
  `enable_toolset("native")`; evidence memory persists in
  `analysis/l2-godot.cany/` (do not delete); it has NO UE2/L2 package readers —
  `tools/l2strict` stays the asset path. `tools/uelib-test` — Eliot.UELib
  (C#, dotnet 10) loads our ver 123/23 packages but also has no StaticMesh
  geometry class. Client binaries are at LOWERCASE
`/Games/ElmoreX3/system/` (`l2.exe`, `engine.dll`, …) — native RE targets
exist there (engine.dll already mined for `AActor::LocalToWorld`).
Details: `Docs/craft-anything.md`.
- `_ue_basis(pitch, yaw, roll)` in `scripts/world.gd` is the UE2
  FRotationMatrix closed form; the naive `Roll*Pitch*Yaw` Euler product is
  NOT equivalent — never replace it. Angles wrap with `& 0xFFFF`.
- The user's DXVK/CACAO setup dumps `/Games/ElmoreX3/system/cacaodump_*.pgm`
  (AO/depth/ssao) from live original-client frames; currently black/flat, so
  not usable as geometry references.

## Godot 4 / GDScript quirks discovered this session

- `:=` cannot reassign an already-declared variable; use plain `=` after the
  first declaration (caused parse errors on `frac := ...` second write).
- `Image.load()` is an instance method: `var img := Image.new()` then
  `img.load(path) == OK`; `Image.load(path)` as a static call fails.
- `PackedByteArray` (from `Image.get_data()`) has no `get_pixel()`; use
  `Image.get_pixel(x, y)` directly on the `Image`.
- GDScript has no accessible enum path for material blend modes
  (`BaseMaterial3D.AlphaBlendMode...` unresolved), so only
  `alpha_scissor_threshold` is set for transparent textures; blend mode is
  left default (opaque).
- GDScript cannot infer types from `mesh.surface_get_arrays()` — all vars
  need explicit `: float`/`: int` annotations (otherwise "Cannot infer the
  type" parse errors).
- GDScript does not support set-like dictionary `{ "a", "b" }`; use `[]`
  Array with `key in array` membership test.
- GDScript ternary syntax is `value if condition else other`, NOT
  `condition ? a : b`.
- Multi-variable typed declaration `var i0, i1, i2: int` is invalid; declare
  each separately.

## Current strict pipeline (`tools/l2strict`)

- Use `tools/l2strict`, not the legacy `tools/l2_*.py` scripts, for all new
  map work. Legacy scripts and `18_20` assets are kept only for comparison.
- Build one tile:
  `python3 -m tools.l2strict build --source-root /Games/ElmoreX3
  --work-dir tmp/l2/<map> --map <map> --assets-dir assets/maps/<map> …`
- Verify one tile:
  `python3 -m tools.l2strict verify --work-dir tmp/l2/<map>
  --assets-dir assets/maps/<map> --map <map>`.
- The strict property parser also extracts legacy `18_20` with zero errors;
  it is not specific to `20_18`.
- `assets/maps/<map>/map.json` is a BUILD ARTIFACT — never hand-edit it
  (hand-lifted bridge Z caused the "two bridges" defect, 2026-11-02).
  Regenerate with `python3 -m tools.l2strict extract <unr> --out …`; audit
  suspicious actors by re-extracting and diffing against the package.
- Terrain heightmap anchoring formula is **verified** for `20_18`: derive
  origin from `TerrainInfo.Location`, `TerrainScale`, `MapX`, and `MapY`,
  not from the filename; border samples come from the real neighbor
  heightmaps (`21_18`, `20_19`, `21_19`).
- Terrain holes (Dark Elf Village cutout): `QuadVisibilityBitmap`
  `surface_present == 0` means "no valid terrain surface here". Hole cells
  hold placeholder raw 2511 (z ≈ −8821.9) and must not be rendered,
  collided, or sampled for ground height. The terrain mesh skips hole quads;
  `has_terrain_surface(game_x, game_y)` in scripts/world.gd guards
  `terrain_height()` and the player's height clamp in scripts/player.gd.
- The hole is filled by village static meshes (`O_DE_MT_Out/In/Btm`,
  `O_De_03`, `O_DE_Btm*` …). Any static mesh whose world AABB covers a hole
  cell gets a trimesh collider (`_covers_terrain_hole` + `_trimesh_cache` in
  scripts/world.gd).
- Player spawn is hole-aware: if the `PlayerStart` cell has no surface, use
  the stored `PlayerStart` Z plus 0.9 m clearance instead of sampling the
  heightfield (all five `20_18` spawn cells are holes).
- Package import names and filenames differ in case on Linux
  (e.g. `Oren_DEV_T` vs `oren_dev_t.utx`). `asset_map.json` records the
  canonical staged package for every actor mesh; do not build asset paths
  directly from import package names.
- L2 `Matrix` and `Plane` structs are nested property lists, not raw
  16-float/4-float binary values.
- `T_ARRAY` declared size includes the compact count bytes; payload size is
  `size - count_bytes`.
- The first element of a repeated property array may be written without the
  array flag; the parser must promote that scalar to a list when the next
  indexed element appears.
- Terrain UVs use `su = 2 * layer.Scale.x / (128 * 128 * UScale)` and the
  matching V formula; masks use tile UV `0..1`.
