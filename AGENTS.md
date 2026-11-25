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

## GOLDEN BASELINE (2026-11-15) — the approved road look; do not regress it

- **The commit: 54dadb9, the git tag: `golden-road-20261115`.** The baseline
  renders: `Docs/baseline/*.png` + `Docs/baseline/MANIFEST.md` (the exact
  reproduction commands for the five named viewports).
- **The state:** the road pieces render their AUTHORED textures and UVs
  (no world-uv, no substitutions, no road samplers); Polys3977/3987 hidden
  (hide-redundant); the wheel zoom + the camera collision live; L2_BRIGHT
  works.
- **ANY change to the road/floor visuals is verified by the pixel-diff
  against the baseline renders at the SAME camera** (the fresh
  `rm -rf .godot/imported` + the full import before every render — the
  renders without it are VOID). A deviation beyond the noise at a baseline
  viewport = the regression, not "verified".
- **The forbidden moves** (each cost real iterations 2026-11-13–15):
  substituting the authored road textures (dark01/wall05 → floor01 stripped
  the texture variety — rejected); the world-uv override on the road (the
  progressive degradation of the authored mapping across 149275f/ede3c12/
  a51b955); the road-piece height offsets without the user's approval of
  the visual result; the road geometry rebuild (rolled back twice:
  cce5af0, 45a4d10).
- **The texture-variety rule:** the entrance/descent texture variety
  (DE_V_floor cobble + O_dark_01 plates + wall05 plates + capet carpets, as
  the original meshes assign) is the USER-APPROVED look. One-texture
  unification of the road was tried (064b0a8, the mandate v2) and
  rejected — do not repeat without a new explicit order.

## Verification harness (MANDATORY pre-commit protocol for shader /
## material / geometry fixes — established 2026-11-14 after the "fix not
## visible" loop repeated 4 times)

An iteration counts as "verified" ONLY with all five gates green (numbers
in the DEVLOG entry), plus the meta-gate before any rebuild:

- **Gate A — the shader actually compiled.** Godot silently falls back when
  a shader fails to compile (2026-11-06: an undeclared identifier → fallback
  → ALL edits invisible). Capture the FULL render stderr and require 0
  lines matching `shader error|compile` — and 0 hot-pink leftovers after a
  gate-D run. "Verified by render" without this = invalid.
- **Gate B — pixel diff at the USER'S NAMED viewport** (fixed camera, e.g.
  7482,17753 / 7666,17666 / 10636,17048 / spawn): ≥ 1000 changed pixels AND
  the direction matches the expectation. No pixel movement → no commit →
  no "verified".
- **Gate C — trace-box BEFORE writing the fix** (`L2_TRACE_BOX`): which
  mesh / layer (BSP vs static) / texture does each road pixel hit? Fix ONLY
  the layer the trace names. 2026-11-13–14: three iterations were spent
  fixing the BSP layer while the visible road was the static meshes
  (O_DE_Btm_Obj01 sits 10 cm ABOVE the BSP plates).
- **Gate D — assert the branch fires.** Any conditional in a shader (e.g.
  a horizontal-face guard): temporarily set `ALBEDO = vec3(1.0, 0.2, 0.8);`
  on the taken branch, screenshot, verify the coverage matches the expected
  region and nowhere else, THEN remove the debug output.
- **Gate E — lint: world-space effects read NO VERTEX/NORMAL in
  fragment().** In Godot 4 fragment VERTEX/NORMAL are VIEW-space even with
  `world_vertex_coords`. World effects read ONLY `varying vec3 wpos` written
  in vertex(), with the normal via `normalize(cross(dFdx(wpos),
  dFdy(wpos)))`. (2026-11-14: a view-space normal guard made the world-uv
  override almost never fire.)
- **Meta-gate — query the memory BEFORE any "redo X from scratch / clean
  room".** Check craft-anything investigation memory + DEVLOG for "was X
  attempted → rolled back?". The road geometry rebuild was attempted twice
  and rolled back (cce5af0, 45a4d10) — the seam is solved at the UV-sample
  level (world_uv_scale + TEXTURE_SUBSTITUTE), not at the vertex level.

**Rebuild rules (MANDATORY, 2026-11-18):** one session burned ~300k
tokens on rebuild iterations that changed nothing visible. The full
protocol — incremental rebuilds per region (never all 26 meshes for one
fix), the stale-cache rule, reproduce the user's camera first, trace
before fixing, one hypothesis per iteration, the 2–3-render cost budget
— lives in `Docs/REBUILD_RULES.md`. Read it before any fix/rebuild loop.

Reimport trap (both bit us): after regenerating glTFs delete
`assets/maps/20_18/meshes_bsp/*.import` AND after shader edits delete
`assets/shaders/*.import`, then `rm -rf .godot/imported` + a full
`godot --headless --import` — the cache does not reliably refresh.

Diagnostic coordinate units: `L2_STEP_TEST` uses Godot meters, but
`L2_FLOOR_GRID`, `L2_FLOOR_PROFILE`, and `L2_TRACE_RAY` take raw L2 game
units (for example `14825,16123`, not `148.25,161.23`). Mixing them silently
probes the world origin and produces plausible but irrelevant terrain hits.
- `FBspSurf.idx[4]` is `iBrushPoly`, NOT an index into `Model.Nodes`. The
  legacy `levelbsp.py` used it as a node index and stamped stale CSG floor
  records onto native interiors. The corrected generator drops
  `DE_V_floor01`/`Iron_net` entries when the node authority is `DE_V_floor02`,
  after canonical UV selection so surviving road UVs stay unchanged.

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
  (saves shot1/shot2.png then quits); render on the REAL display
  (`godot … --rendering-driver opengl3` with DISPLAY=:0 — radeonsi/RX 6400,
  a render ~21 s; a game window flashes on the desktop, that is expected).
  `xvfb-run -a … godot …` = the llvmpipe fallback ONLY (8x slower AND
  different pixels — never pixel-diff llvmpipe shots against the GPU
  baselines). `L2_VIEW_YAW` overrides spawn view yaw;
  `L2_BRIGHT=1` (diagnostic only, isolated in `_build_environment()`)
  forces flat white ambient so black regions are recognisable as missing
  geometry rather than shadowed dark textures.
- **MCP servers registered (need ZCode restart to appear in tool list):**
  Craft Anything **0.6.0** (`~/.local/bin/craft-anything-cli mcp --project
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

## The foliage/trees pattern (PERMANENT rule — the user's directive, 2026-11-21)

Every tree/foliage family in EVERY tile — the existing ones and every
new tile — goes through the full pattern. No per-tile exceptions, no
"old type" leftovers. When a new tile brings new tree/foliage families,
CHECK them against all five points before the tile is called done:

1. **MultiMesh batching** — one `MultiMeshInstance3D` per mesh key
   (the DEVLOG-86 path), never per-actor `MeshInstance3D` clones.
2. **Alpha scissor BY CONTENT** — a foliage texture gets
   `TRANSPARENCY_ALPHA_SCISSOR` (0.35) when the texture IMAGE itself
   has a real alpha channel (`Image.detect_alpha()`), NEVER by the
   texture name. The new tiles name their moss/leaf textures without
   "leaf"/"grass" (the 19_19 Darkelf_tree08 moss cards, the tomb
   banners, the guard's flag rendered as OPAQUE cards — the user's
   report). The name check remains ONLY for the non-foliage keys (the
   carpet alpha = a specular/blend mask — never cut).
3. **Trunk cylinder colliders** — from the bark-surface AABB,
   positioned at the BARK CENTER (not the mesh pivot — off-center
   meshes exist), rotated by the instance basis. The canopy cards are
   NEVER solid: a tree key without a trunk entry is pass-through, and
   the boot prints `WARN: tree key without trunk collider` — that WARN
   is a pattern violation, not an acceptable state.
4. **Visibility ranges** — the trees 260 m, the grass 70 m.
5. **The per-tile verification** — the boot log must show
   `trunk colliders for N tree meshes` with N = ALL of the tile's tree
   keys; a close-up screenshot of every NEW tree family (the alpha
   check against the client); `L2_TRACE_RAY` through a canopy returns
   no card hits.

## The modern-port rule (the user's directive, 2026-11-12; extended 2026-11-16)

- **NEVER port the original's crutches** (the user's rule, restated
  2026-11-16 after the temple subtract-brush incident): any outdated logic
  of the legacy client — the CSG brush carving, subtractive/additive volume
  emulation, invisible zone-separator boxes (the 0x40a000 family), the
  2000s level-design hacks — is a priority error to reproduce. This covers
  levels, effects, and everything else.
- From the old client we take ONLY: **the geodata and the coordinates.**
  Meshes — if they are clean (bug-free); if building them from scratch is
  cleaner, we CREATE them instead (the temple interior is the example: the
  client authors it as subtract volumes, we emit a clean native mesh from
  the client coordinates — tools/l2strict/temple_native.py).
- The levels are built with modern and optimized Godot 4 means (native
  nodes, materials, shaders, visibility ranges, LODs).
- Textures are NOT ported verbatim as PNG files. They are CREATED with
  modern methods (procedural/3D/volumetric Godot materials, no PNG), using
  the clean-room approach with the condition of a 1:1 visual identity to
  the original client.
- Verification = the mandatory screenshot comparison against the original
  (Docs/DE_village.png and the user's captures) for every new material.
- **NEVER break what already works** (the user's rule, 2026-11-17): the
  village (the road, the tunnel, the spawn flow) was working — any change
  outside the current task region that touches the working areas is a
  regression by definition. The golden-road baseline pixel-diff gates this
  for the road; for everything else, changes must stay inside the task's
  region (e.g. the temple work may not alter the village).

## The weather scope (PERMANENT rule — the user's directive, 2026-11-21)

The overcast sky + the day/night cycle (DEVLOG-120..122) apply ONLY to
the currently built maps (the Dark Elf territories: 20_18, 20_17, 21_18,
19_18, 19_19, 18_19). The border zones between the DE territory and the
rest of the world will be adjusted MANUALLY per-zone, never as a global
weather for all maps. Every NEW map (a new territory) gets its OWN
individual weather. Do not extend the sky/weather system beyond the
built DE tiles without the user's explicit per-map order.
