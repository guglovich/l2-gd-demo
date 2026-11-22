# Godot rebuild rules (the $150 lesson, 2026-11-18)

One session burned ~300k tokens ($150) on rebuild iterations that changed
nothing visible. Every rule below is a named incident, not a guess.
Follow them in order; they exist so this never repeats.

## Rule 1 — Never rebuild the whole project for a local change

The build is incremental BY REGION. A fix in one mesh/one shader/one
region rebuilds ONLY that artifact:

| Changed | Rebuild | NOT this |
|---|---|---|
| one static mesh | `static_gltf_from_parse.py <pkg.usx> <dir> <MeshName>` | all 26 temple meshes |
| temple BSP | `temple_bsp.py <unr> <asset_dir>` | village levelbsp/brush |
| one texture/material | `world.gd` reads `temple_bsp.json` / `asset_map.json` — regenerate only the touched json entry | the whole asset_map |
| a `.gd` script | nothing — scripts are not imported | any reimport |
| a `.gdshader` | delete `assets/shaders/*.import` only | glTF imports |

A full `rm -rf .godot/imported` + 2-minute headless import is REQUIRED
only when binary-imported assets changed (glTF/bin/shader/PNG). It is a
WASTE for script-only edits — do not run it, do not wait for it.

## Rule 2 — The reimport trap: stale cache = "fix not visible"

`rm -rf .godot/imported` + `godot --headless --import --path .` must run
between regenerating any asset and ANY verification render. Three
mid-stream verifications ran against stale caches and reported "no
change" on fixes that were actually correct (DEVLOG-84). If an iteration
shows zero visual movement, the FIRST suspect is the import cache, the
second is that the edited code path never executed (Rule 4), and only
the third is the fix itself being wrong.

## Rule 3 — Reproduce the user's camera BEFORE writing any fix

Every blind-iteration loop started with renders from my own cameras while
the user's defect lived at their exact position and yaw. Protocol:

1. Read the position off the user's screenshot title bar
   (`X=… Y=… Z=…`), not from memory.
2. Reproduce it: `L2_SPAWN="x,y,z"` + `L2_VIEW_YAW=…` (+ `L2_VIEW_PITCH`
   if vertical). Get the yaw/pitch from what is visible in the frame.
3. Only then diagnose, fix, and verify AT THAT CAMERA.

## Rule 4 — Prove the code path runs (Gate D applies to GDScript too)

2026-11-13 (7f70dfd): an Edit silently did not land (a "2 matches"
guard) and the "verified" render was of code that never ran. Before
declaring a fix live:

- `git diff` the file and READ the diff — confirm the change is in the
  branch that executes for the current build path.
- For conditionals (env flags, `texel_uvs`, `cull_back`): force the
  branch and confirm the effect on screen once, then revert the forcing.
- A parse error in any `.gd` kills EVERYTHING (renders hang/exit 124) —
  `godot --headless --check-only --script scripts/world.gd` (or just a
  5-second headless run) after every script edit before any long render.

## Rule 5 — Trace before fixing (Gate C)

`L2_TRACE_BOX` / `L2_TRACE_RAY` / `L2_FLOOR_PROFILE` name the owning
mesh, layer (BSP vs static vs terrain) and texture BEFORE any edit.
2026-11-13–14 burned three iterations fixing the BSP layer while the
visible surface was a static mesh 10 cm above it. Never fix a layer the
trace did not name.

## Rule 6 — One hypothesis per iteration, A/B with env flags

Diagnostics that flip behavior WITHOUT a rebuild (`L2_BSP_2SIDED`,
`L2_BRIGHT`, `L2_FLAT_DEBUG`, `L2_GREY_DEBUG`, `L2_NO_LEVELBSP`) are the
cheapest instrument in the project: they isolate a layer in ONE render.
Before any geometry/material change, run the env-flag A/B that could
explain the defect. Do not stack multiple fixes into one rebuild — when
the result is wrong you cannot tell which change did it, and you pay a
full render cycle to separate them again.

## Rule 7 — Cost discipline per iteration

One normal iteration = 2–3 renders maximum: (1) the diagnostic or
A/B render, (2) the fix verification at the user's camera, (3) the
baseline/golden-road guard when the change could touch an approved area
(the pixel-diff against `Docs/baseline/*.png`). Renders run headless via
`xvfb-run -a godot --rendering-driver opengl3`; a hung render (>2 min
with no screenshot) = kill it (`pkill -9` the stray process — a stuck
background render once hogged the whole machine and every later render
timed out) and fix the cause, do not queue more renders on top.

## Rule 8 — After every rendered verification: numbers in DEVLOG

An iteration without its numbers (Gate A stderr shader-error count,
Gate B pixel counts, profile lines) did not happen. The DEVLOG entry is
written in the SAME turn as the verification, not at the end of the
session from memory.

## Import cost (measured 2026-11-20, the multi-tile world)

- `tmp/.gdignore` is MANDATORY: without it Godot's import scans tmp/'s
  22 862 junk files every run — the no-op import was 36 s; with the
  ignore file it is **4 s**. The full `rm -rf .godot/imported` + import
  = ~36 s (the real re-import of ~6.6k asset files).
- The tile builds are INCREMENTAL: a repeat `build` of an already-staged
  tile = ~3 s (the manifest hashes skip the UModel exports and the
  decodes). The FIRST build of a new tile pays the one-time UModel
  export + decode cost (minutes).
- The per-tile builds are independent: editing 20_18's assets does NOT
  rebuild 19_18/20_17/21_18 (their staged hashes are unchanged; their
  builds only run when explicitly invoked).
- The runtime load grows ~1.5-1.7 s per tile (4 tiles = ~6.6 s).

## Where an iteration's CPU actually goes (audit 2026-11-20, DEVLOG-110
## addendum 4)

The build/import is NOT the cost: a repeat `build --assets-dir` = 9 s
(it re-runs all ~237 per-object UModel exports, ~25 ms each — wasteful
but harmless), `godot --import` = 3.6 s with ZERO re-imports (Godot 4.7
re-imports by source MD5, not mtime — re-staging identical content
triggers nothing; docs: tutorials/assets_pipeline/import_process.html).
**The cost is the RENDERS**: one standard L2_SCREENSHOT run = 166 s wall
at 720% CPU (~20 CPU-minutes), of which 117 s = the 90-rendered-frame
settle on llvmpipe. An iteration chains 3-5 renders = the CPU pegged
for ~10-15 wall minutes — what the task manager shows as "the build".
Corollary: the settle (and the render count) is the first lever to
cut, the build never was the problem; project splitting gains nothing
for the import, which is already per-resource incremental.

## Render harness (fixed 2026-11-20, DEVLOG-111 — the user approved A+B)

- **The renders run on the REAL display** (`DISPLAY=:0`, no xvfb):
  `godot --path . --rendering-driver opengl3` picks radeonsi / Radeon
  RX 6400 — one render = **21-22 s** (was 166 s on llvmpipe). A game
  window flashes on the desktop for those seconds — expected.
- **xvfb-run = the llvmpipe FALLBACK only** (8x slower AND different
  pixels): never pixel-diff llvmpipe shots against the GPU baselines.
- **The settle counts PHYSICS TICKS** (`_await_settle_ticks` in
  world.gd, default 720 = 12 s of game time; `L2_SETTLE_TICKS`
  overrides), **anchored AT THE SPAWN** (`_spawn_physics_frame`): the
  frames between the spawn and the settle loop carry a machine-
  dependent tick drift (the first-frame shader-compile hitch), and
  12 s of tumbling down the descent stairs amplifies it into a
  different place — unanchored, the descent differed by 1.12M px
  run-to-run; anchored, it is 0 px. Do NOT raise
  `max_physics_steps_per_frame` in the settle (it trades exactness
  for speed).
- **The diagnostic runs IGNORE ALL USER INPUT** (`player.input_locked`
  + `WINDOW_FLAG_NO_FOCUS`, set by world.gd when L2_SCREENSHOT/L2_BURST
  is present): the renders run on the real desktop in parallel with
  the user's work — their right-drag orbits the camera, the arrows
  move the character, a click sends it running. The first capture
  attempt was contaminated exactly this way (entrance_road,
  stairway_plaza: 1M px run-to-run). Never remove the lock.
- The golden baselines are RE-CAPTURED on the GPU (the MANIFEST has
  the note); the final GPU-vs-GPU noise floor: **≤30 px >8 per view,
  mean ~0.001**.
- The fresh-import rule stands: one `rm -rf .godot/imported` + import
  before a capture session; the views share it when no assets changed
  between them.

## Process discipline (2026-11-20, the two hangs)

- NEVER launch a godot run without a quit flow (L2_SCREENSHOT /
  L2_BURST): the game idles at 0% CPU forever after the world build —
  a no-quit run hung 7 minutes before the kill.
- NEVER run concurrent godot instances on ONE project dir: 5 parallel
  baseline renders deadlocked at 0% CPU (4 of 5 hung ~10 min — the
  .godot cache contention). The golden baseline stays SERIAL.
