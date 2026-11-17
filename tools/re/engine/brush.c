/* engine.dll — ABrush / the brush rendering facts (2026-11-17).
 * See Docs/EngineRE.md. Entry points verified in the disassembly. */

#include <stdint.h>

/* ---- ABrush::PostLoad @0x10302ab3 (fully decoded, 3 lines of logic) ----
 * void ABrush::PostLoad() { AActor::PostLoad(); }
 * Nothing else: the Brush actors do not transform their geometry at load.
 */

/* ---- The brush rendering facts -----------------------------------------
 * 1. ABrush defaults to DrawType = DT_Model (UE2 stock) — but the 20_18
 *    Brush actors' own UModel ("Brush" property) is an EMPTY model
 *    (257 Model exports; all temple-region ones = 72 B, i.e. no Surfs/
 *    Nodes/Verts). FDynamicActor::Render therefore has no geometry to
 *    draw from them.
 * 2. engine.dll contains NO runtime CSG: searches for Csg/Mod/Carve
 *    symbols return zero. The CSG result is baked into the level's
 *    Model500 by the editor and shipped in the .unr.
 * 3. The temple Brush actors (Polys17, Polys23/28, Polys55/67, Polys51,
 *    Polys71/59, Polys31/35, Polys39, Polys91..163, Polys43/63/83/79/87)
 *    are the CSG SOURCES + the ZONE MARKERS. Their FPoly flags split:
 *      - 0x0040A000 (Unlit|L2:0x2000|L2:0x8000) = the zone-boundary
 *        faces, never rendered (Polys17 all 6, Polys55/67 all 6,
 *        Polys23/28 5 of 6 — textured with the marker stone
 *        oren_sylen_in002);
 *      - 0x0 faces = the real baked CSG surfaces, which live in the
 *        LEVEL BSP (they are also reachable as BSP Surfs via
 *        (Owner Brush, iBrushPoly) — see Docs/EngineRE.md);
 *      - the ZonePortal planes carry 0x04000109 =
 *        PF_Portal|TwoSided|NotSolid|Invisible.
 * 4. CONSEQUENCE for the port: the Brush faces must never be rendered;
 *    the temple interior comes from the level BSP (tools/l2strict/
 *    temple_bsp.py) + the decoration static meshes. The marker-face
 *    texture oren_sylen_in002 = the "gray rectangles" the user saw.
 */

/* ---- FPoly (file record) — from fnd_14, for reference ------------------
 * compact NumVertices + 4 FVectors (Base, Normal, TextureU, TextureV)
 * + N x FVector + DWORD Flags + objref Actor (+0xF4) + objref Material
 * (+0xF8) + FName Item (+0xFC) + compact iLink (+0x104) + compact
 * iBrushPoly (+0x108) + 2 dwords. */
