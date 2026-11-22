# GOLDEN BASELINE — the road states the user approved (2026-11-15)

The commit: **54dadb9** — the git tag: **golden-road-20261115**.
These renders are the reference. ANY change to the road visuals must
pixel-diff against them. A deviation beyond the noise = the regression.

**RE-CAPTURED 2026-11-20 on the real GPU** (DEVLOG-111): the five PNGs
were re-rendered with the same cameras on **radeonsi / Radeon RX 6400**
(the real X display, `godot --path . --rendering-driver opengl3`, no
xvfb). Three reasons: (1) the render harness moved from llvmpipe (CPU)
to the GPU — a render 166 s → 21 s; the GPU-vs-llvmpipe rasterizer
noise (~1-14k px >8 per view) exceeds the diff gate, so the references
must be GPU-rendered; (2) the settle now counts PHYSICS TICKS anchored
AT THE SPAWN (`_spawn_physics_frame`, 720 = 12 s of game time,
renderer- and machine-independent) — the old 90-awaited-frame settle
gave a machine-dependent game time; (3) the diagnostic runs IGNORE
ALL USER INPUT now (input_locked + WINDOW_FLAG_NO_FOCUS): the first
capture attempt was contaminated — the user's own right-drag rotated
the camera mid-render (the game runs on the real desktop in parallel
with the user's work). The descent reference additionally refreshes
its stale far field (the terrain LOD 5000 m changed the far-south
pixels since 2026-11-15). Final run-to-run determinism (every view
rendered twice): **≤30 px >8 per view (worst: upper_street), mean
delta ~0.001** — the llvmpipe-era gate noise level.

## How to verify (the exact commands)

```
rm -rf .godot/imported
godot --headless --import --path .
L2_SPAWN=<spawn> L2_VIEW_YAW=<yaw> L2_ZOOM=<zoom> \
L2_SCREENSHOT=<abs dir> godot --path . --rendering-driver opengl3
```
Run godot on the REAL display (DISPLAY=:0, radeonsi), NOT under
xvfb-run — xvfb forces llvmpipe (8x slower, different pixels: never
pixel-diff llvmpipe shots against these GPU baselines). The
diagnostic runs lock all user input automatically (L2_SCREENSHOT sets
input_locked + WINDOW_FLAG_NO_FOCUS — the user may keep working; the
game ignores their mouse/keyboard). One fresh import before a capture
session; the five views share it when no assets changed between them.
Then pixel-diff `shot1.png` vs the matching baseline PNG here. The
baseline noise floor (GPU vs GPU): **≤30 px >8, mean ~0.001**.

## The five baselines

| view | L2_SPAWN | L2_VIEW_YAW | L2_ZOOM | file |
|---|---|---|---|---|
| the upper street at the entrance | 7482,17753,-4402.4 | 49152 | 0.5 | upper_street.png |
| the entrance road | 7682,17689,-4404.5 | 49152 | 2.4 | entrance_road.png |
| the descent | 8484,17511,-4600.1 | 32768 | 1.5 | descent.png |
| the stairway plaza | 10636,17048,-4610.9 | 16384 | 1.2 | stairway_plaza.png |
| the spawn plaza | 10741,16930,-4628.9 | 16384 | 1.0 | spawn_plaza.png |

## What this state contains (the approved look)

- The road pieces render their AUTHORED textures and UVs (DE_V_floor cobble,
  O_dark_01 plates, wall05 plates, capet carpets — as the original meshes
  assign). NO world-uv override, NO texture substitutions, NO road samplers.
- Polys3977/Polys3987 hidden (hide-redundant: covered by the statics).
- L2_BRIGHT works (the zone ambient no longer overwrites the diagnostic).
- The wheel zoom (0.35..2.6) + the camera collision live.
- The spawn-plaza dark01 plates = dark01 (restored; NOT substituted).

## The forbidden moves (the burned-token lessons, 2026-11-14)

- DO NOT substitute the authored road textures (the dark01/wall05 ->
  floor01 substitutions stripped the texture variety — the user rejected).
- DO NOT apply the world-uv override to the road (it degraded the authored
  mapping progressively across 149275f/ede3c12/a51b955).
- DO NOT offset the road pieces' heights without the user's explicit
  approval of the visual result (the v3 offsets removed the ledges but the
  accompanying texture trade was rejected).
- DO NOT rebuild the road geometry (the clean-room rebuilds rolled back
  twice: cce5af0, 45a4d10).

## The verification rule (AGENTS.md)

Every verification render runs after a FRESH
`rm -rf .godot/imported` + the full import. The renders without it are
VOID (the stale compiled state rendered dark/light incorrectly — the
2026-11-14 loop).
