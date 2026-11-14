# GOLDEN BASELINE — the road states the user approved (2026-11-15)

The commit: **54dadb9** — the git tag: **golden-road-20261115**.
These renders are the reference. ANY change to the road visuals must
pixel-diff against them. A deviation beyond the noise = the regression.

## How to verify (the exact commands)

```
rm -rf .godot/imported
godot --headless --import --path .
L2_SPAWN=<spawn> L2_VIEW_YAW=<yaw> L2_ZOOM=<zoom> \
L2_SCREENSHOT=<abs dir> godot --path . --rendering-driver opengl3
```
Then pixel-diff `shot1.png` vs the matching baseline PNG here.

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
