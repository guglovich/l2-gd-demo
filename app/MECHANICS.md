# Lineage 2 (ElmoreX3) — Decompiled Mechanics

Evidence-backed values, formulas, and rules extracted from the original client binaries with Craft Anything (Deep mode, builtin x86 disassembly). These replace/justify guessed values in the Godot reimplementation.

## Source targets (opened with `core_target_open`)

| Target | Kind | SHA-256 | Craft target id |
|---|---|---|---|
| `/Games/ElmoreX3/system/l2.exe` | PE (Windows) | `bd1013164257c0f0d5b727032059fd51470bd223922554f5945df1ec4a9e3b13` | `t_bd1013164257` |
| `/Games/ElmoreX3/system/engine.dll` | PE32 (Windows), image base `0x10300000` | `974810cad7f04f80b8ce81ce19c4ad44fbd3447bb6b7c8c27fd90725c22e7e1e` | `t_974810cad7f0` |

`engine.dll` is the primary source for the mechanics below (UE2/Lineage2 engine code). `l2.exe` was opened but the relevant gameplay/render property names and formulas are not stored as discoverable strings in the launcher; they reside in `engine.dll`/game modules.

## 1) Terrain quad visibility (render/cutout)

**Function:** `ATerrainInfo::GetQuadVisibilityBitmap(int x, int y)` (`?GetQuadVisibilityBitmap@ATerrainInfo@@QAEHHH@Z`)  
**Address:** `0x1030fde4` (21 instructions, builtin x86 disassembly; body at `0x103783c0`)  
**Observed (disassembly):**
- `width = [ecx + 0x210C]` (terrain quad width/stride field)
- `index = y * width + x`  (`imul eax,[esp+8]`; `add eax,[esp+4]`; __thiscall args x@`[esp+4]`, y@`[esp+8]` in the thunked body context)
- `bitmap_base = [ecx + 0x219C]`
- `word = bitmap_base[index >> 5]`
- `bit = 1 << (index & 0x1F)`
- returns nonzero iff `(word & bit) != 0` (`neg/sbb/neg` idiom)

**Rule:** quad `(x,y)` is visible/rendered when the visibility bit is set. A clear bit means no valid terrain surface at that quad (L2 village/tunnel/cave cutouts use this).  
**Godot mapping:** `world.gd` filters quads with `surface_present_u8.raw` (`terrain_present[q] == 1`, `q = y*terrain_width + x`) — consistent with the bitmap semantics (present/visible = 1). Keep this rule.

## 2) Light radius (world)

**Function:** `ALight::WorldLightRadius()` (`?WorldLightRadius@ALight@@UBEMXZ`)  
**Address:** `0x1030872e` (9 instructions; body at `0x10343130`)  
**Observed (disassembly + data read):**
- loads `LightRadius` (float) from `[ecx + 0x3C4]`
- adds qword constant at VA `0x10852238` (file off `0x552238`, PE base `0x10300000`) = **`1.0`** (`0x3ff0000000000000`)
- multiplies by qword constant at VA `0x10854b50` (file off `0x554b50`) = **`25.0`** (`0x4039000000000000`)
- returns float

**Formula (UE2 units):**
```text
WorldLightRadius = (LightRadius + 1.0) * 25.0
```

**Godot mapping:** convert UE2 units to meters with `UNIT_SCALE = 0.01`: `omni_range_m = (light_radius + 1.0) * 25.0 * UNIT_SCALE`. Applied in `scripts/world.gd` (`_build_lights`). Light *brightness/energy* exact engine-to-Godot mapping was **not** recovered from decompiled functions in this pass (no `LightBrightness` string/function resolved to a decompilable formula here); the existing energy scaling remains an adaptation and is documented as such.

## 3) Actor rotation → world transform (UE2 FRotationMatrix / LocalToWorld)

**Function:** `AActor::LocalToWorld()` (`?LocalToWorld@AActor@@UBE?AVFMatrix@@XZ`)  
**Address:** `0x10304ad9` (234 instructions; body at `0x103277b0`)  
**Related:** `AActor::BillBoardLocalToWorld` @ `0x10312724` uses the same rotation/trig construction pattern.  
**Observed (disassembly):**
- Reads `GMath` table base from `[0x11d8d738]` (`__imp_?GMath@@3VFGlobalMath@@A`).
- Reads rotation components (ints) from actor: Pitch `+[ecx+0x1C8]`, Yaw `+[ecx+0x1CC]`, Roll `+[ecx+0x1D0]` (used to compute sin/cos).
- **Angle/index conversion:** for an angle value `v`, computes `index = (v >> 2) & 0x3FFF` for sin via `GMath + index*4 + 0x8C`; cos uses `(v + 0x4000) >> 2 & 0x3FFF` (quarter-turn offset). This reflects UE2's 65536-units-per-circle fixed-angle representation (`>>2` gives 16384-entry table indexing; `0x4000` in the pre-shift space is the 90° offset for cos).
- Reads Location from `+[ecx+0x1BC/0x1C0/0x1C4]`.
- Reads DrawScale from `+[ecx+0x27C]` and scale components from `+[ecx+0x280/0x284/0x288]` (applied as scaled factors).
- Builds the full 4x4 local-to-world matrix (x87 FPU sequence stores rows/translation into output matrix).

**Rules/notes:**
- UE2 rotation units are **65536 per full circle** (uint16 wrapping is the natural representation; code masks/indexes accordingly).
- `FRotationMatrix(Pitch,Yaw,Roll)` is the canonical UE2 construction; the naive `Roll*Pitch*Yaw` Euler product is **not equivalent** (project rule, consistent with engine using trig-table rotation matrix construction).
- DrawScale is applied as part of the transform (separately multiplicative factors appear in the matrix build).

**Godot mapping:** `scripts/world.gd::_ue_basis(pitch,yaw,roll)` implements the UE2 FRotationMatrix closed form with `& 0xFFFF` wrapping and `tau/65536` angle conversion, then maps UE axes to Godot (y/z swap) — **keep this implementation** (it matches the engine's rotation-matrix approach; do not replace with Euler product). `draw_scale` is applied separately on the instance, which is consistent with the engine separating scale factors.

## 4) Terrain layer texture coordinates

**Function:** `ATerrainInfo::CalcLayerTexCoords()` (`?CalcLayerTexCoords@ATerrainInfo@@QAEXXZ`)  
**Address:** `0x10306915` (679 instructions; builtin study evidence `ev_382ca849899ed0762984eaddd6c4fa21dbe687ddd08c632a08179e5e70795a13`, 17 blocks, 12 callees).  
**Observed (summary):** non-trivial function computing terrain layer UVs; full lifted pseudo-C is large/incomplete in the clean-room lifter (189 `__asm` sites). The project already applies the verified L2 terrain UV rule (from strict pipeline / prior RE): `uv = quad * 64 / Scale` (detail layers tile densely, base sparsely), with shader scale `256 * 64 / Scale = 16340/Scale` over the 256-quad tile in `world.gd`. **Not contradicted** by this pass; treat as the current working rule and refine only with further targeted decompilation of `0x10306915` if visual mismatch remains.

## 5) Fog / zone (partially located)

**Strings found in `engine.dll`:** `L2DistanceFog::UpdateFog` (`0x10891890`), `L2DistanceFog::CalcFogColor` (`0x10891b10`), `SetCurrentFogRange/Color`, `Reset`, `DISTANCEFOG`/`DISTANCEFOGRANGE` (referenced from `UInput::Exec @ 0x105ade18/0x105adedf`).  
**Observed:** L2 extends fog handling via `L2DistanceFog`. The map's ZoneInfo values (AmbientVector/Brightness, DistanceFogColor/Start/End) are consumed by the Godot environment in `world.gd` from extracted `zones.json`/map data; those ZoneInfo property names were not present as plain strings in `engine.dll` in this pass (properties may live in packages/scripts). **Keep current zone-derived fog/ambient values as extracted from map data**; they are the real per-zone settings for 20_18.

## What was *not* fully recovered in this pass

- Exact `LightBrightness` → render/energy formula (no decompilable symbol resolved). Brightness/energy in Godot is an adaptation.
- Full pseudo-C for `LocalToWorld`/`CalcLayerTexCoords` from Ghidra (Deep engine produced `MIPS:LE:32` bad-data results due to language/analysis mismatch in this session); **builtin x86 disassembly** was used as the authoritative observed evidence for formulas above.
- Player walk/run speed constants from native code (no `RunSpeed`/`WalkSpeed` strings in `l2.exe`/`engine.dll`); current Godot speeds are placeholders until traced to movement/actor code or data.
- `L2DistanceFog` method bodies were located by string names but not fully decompiled in this pass (xref at `0x10443c18` not inside a discovered builtin function; needs targeted analysis).

## Build impact

- `scripts/world.gd::_build_lights` updated to use the real `ALight::WorldLightRadius` formula: `((LightRadius + 1.0) * 25.0) * UNIT_SCALE` (meters), replacing the previous `* 6.0` approximation.
- Rotation, terrain visibility, and zone fog/ambient logic already aligned with observed engine rules/extracted data; documented here with function addresses.
