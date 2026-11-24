# 2026 modernization plan — legacy BSP/textures to a unified Godot 4 pipeline

Status: 2026-11-25  
Scope: the built Dark Elf tiles (`20_18`, `20_17`, `21_18`, `19_18`, `19_19`,
`18_19`, `20_19`) and the shared runtime/tools.

This is the migration from temporary compatibility fixes to a reproducible,
modern Godot 4 pipeline. It does **not** change the approved art direction or
the 1:1 geodata requirement. The original client at `/Games/ElmoreX3/` remains
read-only; no synthetic actors/textures are introduced without user approval.

## 1. Goals and hard constraints

1. One authoritative source for every rendered surface, collider and material.
2. No walkable rendered floor without collision; no decorative panel with an
   accidental collider.
3. No overlapping BSP/terrain/static floor copies. Remove masks and height
   patches once geometry is unified.
4. One PBR material model with explicit alpha/height/roughness semantics.
5. Lighting that is stable under camera movement and does not leak through
   walls; no fixed per-material light arrays or renderer light-lottery hacks.
6. A character controller and camera that work in houses, stairs and tunnels
   without teleport assists or roof clipping.
7. Every phase is incremental, committed, numerically verified and reversible.

Non-negotiable gates remain `AGENTS.md` and `Docs/REBUILD_RULES.md`: trace before
fixing, reproduce the user's camera, one hypothesis per iteration, real-GPU
pixel diffs against fixed baselines, zero shader errors, and a spawn screenshot
for every visual change.

## 2. Current architecture (baseline for the migration)

| Layer | Current implementation | Main file(s) |
|---|---|---|
| Terrain | Exact heightfield + `QuadVisibilityBitmap` holes + eight texture layers + custom POM shader | `scripts/world.gd`, `scripts/terrain.gdshader`, `tools/l2strict/terrain.py` |
| Level geometry | Authentic level-Model node/surf walk **plus** reconstructed brush BSP; both render and collide | `tools/l2strict/levelbsp.py`, `bsp2.py`, `scripts/world.gd` |
| Temple | Separate node-walked `TempleBsp` plus clean `temple_native.py` mesh | `tools/l2strict/temple_bsp.py`, `temple_native.py` |
| Statics | UModel glTF, runtime UE basis/scale, optional baked variant | `tools/l2strict/staticmesh.py`, `baked_mesh.py`, `scripts/world.gd` |
| Collision | Terrain/LevelBSP/brush trimeshes; static kDOP subsets; targeted exceptions; foliage trunk cylinders | `tools/l2strict/collision_extract.py`, `scripts/world.gd` |
| Materials | Source PNG + `pbr_albedo`/`pbr_normal` + sidecar; custom PBR/SPOM/analytic shaders; StandardMaterial placeholders | `tools/l2strict/texgen.py`, `scripts/l2_proc_tex.gd`, `assets/shaders/*` |
| Lighting | Sun/moon + cave fade; 32 lantern shader-pool positions; two nearest lantern shadow carriers; 51 candle pool positions; two candle carriers; layer-2 placeholder omnis | `scripts/world.gd`, `scripts/l2_proc_tex.gd`, `assets/shaders/l2_surface_pbr.gdshader` |
| Character/camera | 1.7 m capsule, click-to-move, blocked-target killer, teleport step assist, ray camera collision | `scripts/player.gd` |
| Pipeline | Strict decrypt/extract → UModel → sanitation → texgen → Godot import; JSON/glTF build artifacts | `tools/l2strict/`, `Docs/strict-pipeline.md` |

The current renderer is Godot 4.7 Compatibility/GLES3 (`opengl3` on the test
machine). Custom shaders exist partly because the compatibility renderer has a
small per-object real-light limit; project settings raise it to 256/64, but the
fixed shader pools remain the deterministic path.

## 3. Legacy and temporary-fix register

| ID | Remaining issue / hack | Evidence | Target replacement |
|---|---|---|---|
| G-01 | LevelBSP and brush BSP overlap; native `floor02` and common `floor01` both visible indoors | DEVLOG-165; `Polys154` vs `Polys348/353/3993` | One merged, provenance-tagged zone mesh; delete the native-floor mask |
| G-02 | Static kDOP subsets can omit walkable render floors | DEVLOG-166; `O_DE_inlet` subset has no floor at -41.124 | Corrected collision extraction + automated render/collision coverage audit |
| G-03 | Runtime collision exceptions (`O_DE_inlet` horizontal merge, `store_17` visual-only) | DEVLOG-160/166 | Encode collision intent in the asset manifest; no key-specific runtime branches |
| G-04 | Decorative/full-trimesh collision ambiguity | DEVLOG-160 | Separate render, collision and nav artifacts with explicit flags |
| G-05 | Duplicate/coplanar BSP faces and stale CSG history | DEVLOG-85/165 diagnostics | Deduplicate at extraction; node-authority validation; overlap tests |
| G-06 | Terrain holes filled by multiple static shells; height mismatch risk in tunnels | DEVLOG-85 pending note, DEVLOG-166 | Unified terrain/static contact audit; client pathing/nav source where available |
| M-01 | Stale PBR alpha: source mask rendered as height/opaque | DEVLOG-154/158/164 | Texgen regression fixtures; explicit `alpha_class` in sidecar/import preset |
| M-02 | Albedo A and normal A overloaded (height/roughness); no packed ORM | `texgen.py`, `l2_surface_pbr` | Albedo RGB(A only for true cutout), normal RGB, packed ORM, optional height |
| M-03 | `CONFIG` and `.pbr.json` can disagree; sidecar POM often ignored | `l2_proc_tex.gd` `CONFIG` vs `_load_sidecar` | One material manifest/import preset; no dual configuration |
| M-04 | Per-texture/per-key material clones and runtime exceptions | `l2_plafond`, `l2_frame_pool`, `candle_glow`, floor mask | Imported material resources with standard parameters |
| M-05 | StandardMaterial placeholder surfaces on render layer 2 | DEVLOG-147 | Convert all surfaces to the unified PBR/material path |
| M-06 | Texture compression/import policy depends on headless vs GPU import | AGENTS reimport notes; BC7/S3TC split | Real-GPU import preset, BC7, mipmaps, anisotropy, streaming budget |
| L-01 | Fixed 64-entry lantern/candle shader pools | DEVLOG-147/159 | Clustered/forward+ real lights or a general bounded light manager |
| L-02 | Nearest-two shadow carriers replace pool indices | DEVLOG-150/162 | One shadow/light policy with explicit near/far LOD |
| L-03 | Layer-2 omni routing and render-layer twins | DEVLOG-147 | Single layer/material path; no duplicate mesh instances |
| L-04 | Cave/day-night logic uses global `max(lamp_f, cave_f)` | `world.gd::_update_daynight` | Zone volumes with per-zone lighting profiles |
| P-01 | Teleport step assist + blocked-target killer | DEVLOG-148..157 | Robust capsule step/snap controller driven by collision metadata |
| P-02 | Indoor camera can rise through visual ceilings; camera collision is ray-only | diagnostics, DEVLOG-165 investigation | Camera collision volumes/portals and indoor clearance rules |
| P-03 | Fast tunnel movement exposed fall-through | DEVLOG-166 | Continuous collision/CCD tests plus complete walkable collision |
| Q-01 | Build artifacts and runtime masks are partly hand-maintained | `map.json`, mask PNG, runtime lists | Deterministic generators + manifests + verify gates |
| Q-02 | Legacy/backup code remains active as a trap | `scripts/world_backup.gd`, old `tools/l2_*.py` | Archive/delete after parity; strict pipeline only |

## 4. Target architecture

### 4.1 Geometry and provenance

Produce a per-tile `surface_manifest.json` during extraction. Every triangle
records:

- source (`level_model`, `brush`, `static`, `terrain`, `temple_native`);
- original object/surf/primitive IDs;
- material key;
- render flags (two-sided, cutout, invisible/portal);
- collision flags (solid, walkable, decoration-only);
- nav flags (walkable, slope, stair);
- world AABB and zone/portal ID.

Runtime builds a small number of merged meshes per zone/material from this
manifest. LevelBSP is authoritative where it contains final CSG geometry;
brush geometry is imported only for gaps, never rendered on top of an existing
native surface. Static shells fill terrain holes but do not duplicate BSP
floors. The temple uses the clean native mesh, not subtract-brush emulation.

Collision and navigation are generated separately from render geometry:

- collision = client kDOP subset **plus** validated walkable render surfaces;
- navigation = client pathing/heightfield where available, otherwise a baked
  navmesh generated from validated walkable triangles;
- decoration, glass, grates and portal planes are explicitly non-solid.

### 4.2 Materials and textures

Use imported Godot material resources (`.tres`) or a single data-driven shader
with standard parameters:

- `albedo` (RGB; A only for true alpha-cutout/decal);
- `normal` (RGB);
- `ORM` (occlusion R, roughness G, metallic B);
- optional height for POM/SPOM;
- emission color/energy;
- explicit alpha class: `opaque`, `cutout`, `blend`, `specular_mask`.

Remove the runtime texture-name lists and per-key clones. A material is
classified by source content during extraction, not by a hardcoded object name.
The carpet alpha remains a specular/blend mask unless the client content proves
otherwise (the permanent rule in `AGENTS.md`).

Import policy:

- real-GPU import, BC7/BPTC for opaque PBR sets;
- DXT5/BC7 for cutouts only when alpha quality is verified;
- mipmaps + anisotropic filtering for floors/roads;
- streaming for large atlases;
- deterministic source hashes and import presets in the manifest.

### 4.3 Lighting

Replace the fixed pools and layer-2 twins with one light system:

- near lights are real, shadow-casting and distance-culled;
- far lights are baked/emissive or represented by a cheap analytic term;
- one shadow atlas/LOD policy;
- zone volumes control cave/day/night profiles;
- no per-material light arrays, no nearest-index swaps, no renderer light
  lottery.

A Forward+ clustered renderer is the preferred target if the real GPU passes
the parity/performance gates. Compatibility remains a fallback until then.

### 4.4 Character and camera

- Keep the capsule origin at the feet.
- Use collision-aware step offset/floor snap with source step-height metadata;
  remove teleport landing and the blocked-target killer.
- Add continuous-collision tests for fast tunnel movement.
- Use camera collision volumes/portals with indoor ceiling clearance instead of
  a single ray that can miss visual ceilings.

## 5. Phased roadmap

### Phase 0 — instrumentation and baseline (complete, keep green)

- Golden-road baselines, fixed-time captures, trace/floor-grid tools.
- Per-change Git commit and DEVLOG numbers.
- Exit gate: all five verification gates green; no new runtime hack without a
  tracked replacement item.

### Phase 1 — geometry/collision correctness (highest priority)

1. Audit every static `.collision.json` against its render mesh:
   - walkable render triangles missing from collision;
   - decorative triangles present in collision;
   - duplicate/coplanar faces;
   - invalid winding/AABB.
2. Fix `O_DE_inlet` extraction so the -41.124 floor is in the authentic subset;
   delete the runtime horizontal-merge exception.
3. Resolve `Polys154` native floor vs `Polys348/353/3993` common floor in the
   source manifest; remove `native_floor_mask.png` and the shader discard.
4. Merge/de-duplicate LevelBSP/brush/temple surfaces by zone.
5. Generate collision/nav artifacts with explicit walkable flags.

Exit gate: zero fall-through in tunnel/house floor grids, zero decorative
colliders, no overlapping floor copies, golden-road pixel diff within noise.

### Phase 2 — material/PBR normalization

1. Add texgen regression fixtures for `DE_V_new_deco3`, `doordeco`, candle and
   statue masks; fail the build if source alpha and staged A diverge.
2. Replace albedo-A height / normal-A roughness with packed ORM and optional
   height.
3. Unify `CONFIG` and sidecar into one material manifest.
4. Convert layer-2 StandardMaterial placeholders to the unified PBR path.
5. Apply BC7/mipmap/anisotropy/streaming import presets on the real GPU.

Exit gate: no unresolved/grey/hot-pink surfaces, all alpha classes content
verified, VRAM/texture budgets recorded, user-approved material screenshots.

### Phase 3 — lighting modernization

1. Implement a general near/far light manager and one shadow policy.
2. Replace lantern/candle pools and nearest-two carriers.
3. Remove layer-2 twins and per-material pool exceptions.
4. Move cave/day-night behavior into zone volumes.

Exit gate: no wall light leaks, stable lighting under camera movement, no shadow
atlas eviction, performance budget met, approved day/night/tunnel captures.

### Phase 4 — character/camera/physics

1. Replace teleport step assist with robust step/snap behavior.
2. Add indoor camera clearance/portals.
3. Add CCD/fast-movement tunnel tests.
4. Re-run all house entrances/exits, stairs and tunnel routes.

Exit gate: user-confirmed movement, no pops/falls, deterministic headless
movement tests, spawn screenshot.

### Phase 5 — renderer evaluation

- Benchmark Forward+ vs Compatibility on the real Radeon GPU.
- Compare pixel output, shader variants, light/shadow limits and frame time.
- Switch only after Phases 1–4 are green; keep Compatibility rollback.

Exit gate: approved visual parity or documented intentional improvement,
performance gain, no lost cutout/transparency/shadow behavior.

### Phase 6 — cleanup

- Delete masks, key-specific runtime exceptions, fixed pools, duplicate mesh
  paths, `world_backup.gd` and obsolete tool entry points.
- Keep only strict generators and verification tools.
- Fresh-cache clean build from the original read-only source.

Exit gate: reproducible clean build, no legacy runtime branches, all manifests
and docs match the shipped assets.

## 6. Automation and verification to add

`tools/l2strict/verify.py` (or dedicated audit tools) should fail on:

- a walkable render triangle with no collision triangle below it;
- a collision triangle on a decoration-only surface;
- duplicate coplanar render triangles beyond a defined tolerance;
- overlapping native/common floor polygons from different sources;
- unresolved materials or missing PBR sets;
- source-alpha/staged-alpha mismatch for declared masks;
- more than the configured number of lights/pool iterations per material;
- missing provenance or non-deterministic output hashes.

Runtime diagnostics remain env-gated and numeric:

- `L2_TRACE_RAY`, `L2_TRACE_BOX`, `L2_FLOOR_PROFILE`, `L2_FLOOR_GRID`;
- `L2_SKIP_BRUSH`, `L2_NO_FLOOR_MASK`, `L2_INLET_FULL_FLOOR`;
- fixed-time GPU pixel diffs and golden baselines;
- movement tests through every house door and the tunnel.

## 7. Immediate backlog (next iterations)

1. Re-extract `O_DE_inlet` collision with correct imported winding and walkable
   floor coverage; remove the runtime merge.
2. Run the render/collision coverage audit across every static collision subset.
3. Resolve the native/common floor source overlap and delete the floor mask.
4. Add texgen alpha regression fixtures and the packed ORM output.
5. Benchmark the current 32-lantern + 51-candle pools against a clustered or
   bounded real-light prototype.
6. Remove/ retire `world_backup.gd` after a parity check.

## 8. Guardrails

- No art redesign or synthetic replacement content.
- No modification of `/Games/ElmoreX3/`.
- No mass rebuild or renderer switch before the correctness phases are green.
- No hand edits to `map.json`, glTF, collision JSON or generated masks.
- No visual claim without numeric traces/pixel diffs and the mandatory spawn
  screenshot.
- Every phase is a separate, reversible Git step with DEVLOG evidence.
