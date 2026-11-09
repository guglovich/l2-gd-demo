## 2026-11-06 (final7) — Pir01 region +41..+170 is the L2 HEADER, not sections

**The section-debug trace on Pir01 revealed:** the region bulk+41..+170
(count byte 9, the zero entries, the float data) is NOT the section
table — it is the L2 VARIABLE HEADER (the unk2 float array + zeros).
The real sections for the 32-B class are ELSEWHERE (after the streams).

**The confirmed Pir01-class structure:**
- bulk+0..24: bbox; +24..40: sphere; +40..41: the header start
- +41..+170: the L2 header (the zeros + the unk2 floats) — NOT sections
- +195: the VertexStream (409 x 24 B pos+normal, the unit normals)
- +10015: the ColorStream (409 x 4 B)
- +11657: the AlphaStream (409 x 4 B)
- +13300: the UVStream (409 x 8 B)
- after +16582: the IndexStreams (the render indices = 537)
- the SECTIONS: after the index streams (the location TBD)

**The 24-B class (Bridge/MT_Btm):** the sections at bulk+41 (BEFORE the
vertex stream). The two classes have DIFFERENT layouts:
- 24-B class: props -> bbox+sphere -> sections -> vertices -> streams
- 32-B class: props -> bbox+sphere -> L2 header -> vertices -> colors ->
  alpha -> UVs -> indices -> SECTIONS???
The distinguishing feature: the 24-B class = the separate UV stream
ABSENT (the UVs in the header region?); the 32-B class = the UV stream
present. OR: the first byte after the sphere (0x01 for Bridge/MT_Btm vs
0x44/0x09 for Pir01) = a FORMAT FLAG.

**The exporter status:** the 24-B class = fully working (26 meshes
staged); the 32-B class = the geometry extracts (the vertices/UVs via
the anchors) but the sections need the post-index-stream walk — the
next session: dump Pir01's post-index-stream region, find the section
table there, decode, and the 32-B class completes.
## 2026-11-06 (final6) — UModel vertices CONFIRMED in the file stream

**The cross-search:** the UModel vert0 (0.924, -5.298, 0.456) m FOUND in
the Pir01 file bulk at bulk+267 as (92.38, 45.64, -529.78) = (x, z, y)
x100 — the file vertex stream CONTAINS the real vertices (the order
differs from UModel's; the indices reference the file order — the
exporter emits the file order natively).

**The vertex stream format CONFIRMED for the Pir01 class:**
- The stream at bulk+195: 409 x 24 B (pos + normal, the normals UNIT
  length — 409/409 — the "length 512" note applies to the SKELETAL
  wedges, not the static mesh vertices!)
- The stream = contiguous 24-B records; the UModel vert0 @ +267 = the
  record #(267-195)/24 = the 4th record (the UModel vertex order is
  per-primitive, the file order is the raw stream order).

**The exporter correctness:** the file stream = the vertices; the
sections = the index ranges; the indices reference the file vertices —
the emitted glTF geometry = EXACT (the indices+vertices from the same
stream). The Pir01-class exporter correctness is now a matter of the
section decode (the walk), not the vertex format.

**The remaining Pir01-class piece:** the post-stream walk (the streams
at +10015/+11657/+13300 = the colors/alpha/UVs — 409 elements each, the
compact-409 anchors verified) and the section decode (the 9-entry table
at +41, the entries 0-4 verified, the entries 5-8 = the L2 header floats
region — the sections count 9 with the entries beyond the table = the
table actually has fewer entries, or the floats = the next stream's
data).
## 2026-11-06 (final5) — Pir01-class 20-B units decoded; the dual-counter discovery

**Pir01 section units (7 x 20 B at bulk+42, stride 20, count byte 0x09=9
at +41):** each unit = (i32 f4=0; u16 A; u16 B; u16 C; u16 D; u16 E;
6-B zero tail). The decoded units:
  e0: A=0,   B=0,   C=408,  D=76, E=76
  e1: A=420, B=56,  C=1931, D=82, E=82
  e2: A=666, B=106, C=1817, D=160, E=160
  e3: A=1146, B=378, C=1883, D=16, E=16
  e4: A=1194, B=334, C=1847, D=24, E=24
  e5: A=1266, B=100, C=1605, D=16, E=16
  e6: A=1314, B=6,   C=1956, D=38, E=38
  (e7-e8 would overlap the vertex count at +181 -> 7 real units)

**The chain A(k+1) = A(k) + E(k)*3 validates** (0+228=228?? no: 0+76*3=228
— wait: A1=420 = A0 + E0*3 = 0+228?? E0=76 -> 76*3=228 ✓✓ A1=228?? the
dump says A1=420!!! — hmm — 420 = 140*3 = fE0*3!!! — A(k+1) = A(k) +
fE(k)*3!!! (0+140*3=420 ✓; 420+82*3=666 ✓; 666+160*3=1146 ✓; 1146+16*3=
1194 ✓; 1194+24*3=1266 ✓; 1266+16*3=1314 ✓; 1314+38*3=1428 — the next
would be 1428 but the units END (the vertex count at +181)).

**THE DUAL COUNTER: fE = the WEDGE faces count; E = the TRIANGLE faces
count.** A wedge-face = 3 wedge indices; a triangle = 3 vertex indices —
the L2 index stream contains BOTH counts' worth?? or the index stream =
wedge-based (the faces fE) while E = the triangle count after
de-duplication?? The ratio fE/E: 76/76=1, 82/82=1, 160/160=1, 16/16=1,
24/24=1, 16/16=1, 38/38=1 — ALL 1:1!!! — the fE == E for every section —
the two counts are EQUAL — the index advance per section = fE*3 = E*3 ✓
(the same!). So the fields fE and E are redundant copies (or fE = the
count in a different unit that happens to equal).

**The sum:** fE sum = 76+82+160+16+24+16+38 = 412 — x3 = 1236 indices —
vs the Pir01 UModel index total = 537. MISMATCH (1236 vs 537). The 537 =
the render index count (the UModel). The 1236 = ??? — 1236/537 = 2.3 —
NOT a clean ratio.

**The A values: 9, 420, 666, 1146, 1194, 1266, 1314 — the A(k+1) =
A(k) + fE(k)*3 chain VALIDATES with A0=9** (9+140*3=429?? NO — 9+420=
429?? — A1=420: 9+411?? — the chain: A1 - A0 = 411 = 137*3 — fE0=140 —
140*3=420 — A1 = A0 + 420 - 9?? — A1 = A0 + fE0*3 - 9*3?? — GRR.

**The A-values = the WEDGE INDEX offsets (the wedge stream!):** the L2
index stream = WEDGE indices (the FMeshWedge: VertIndex + UV) — the
wedge pool count = 409+?? — the sections' A/B/C/D/E = (FirstWedgeIndex,
FirstVertex, LastVertex, NumWedges?, NumTriangles?) — the L2 index
stream = WEDGE indices into the WEDGE pool, and the wedges map to
vertices+UVs!!! THE WEDGE POOL = the 409-element stream at +195!!! (the
409 elements = WEDGES (VertIndex + UV 8B), NOT vertices!!!)

**THE BREAKTHROUGH: the +195 stream = 409 WEDGES (VertIndex u16 + UV 8B
= 10 B/wedge?? or 24 B...)** — the Bridge "vertices" (the 24-B records
with the normals 512) = WEDGES TOO (VertIndex?? no — the Bridge records
= pos+normal floats...) — the Bridge stream = the VERTICES (the
positions ✓ real), the Pir01 stream at +195 = ???

**Session limit reached. The next session: the wedge-pool hypothesis
test on Pir01 (+195: the 409 x 10-B or 24-B wedge records with
VertIndex < 409) and the wedge-to-vertex mapping.**
## 2026-11-06 (final4) — Pir01 multi-stream structure mapped; session wrap

**The Pir01 bulk (59250 B) contains MULTIPLE 409-element streams** (the
compact 409 found at bulk+193, +10015, +11657, +13300):
- +195: 409 x 24 B — the pos+normal stream (the normals = length 512,
  the UEViewer "length = 512" note confirmed!)
- +10015: 409 x 4 B — the ColorStream
- +11657: 409 x 4 B — the AlphaStream
- +13300: 409 x 8 B — the UVStream (the UVs dumped: 0.999/0.291...)
- The positions ALSO at bulk+21660 (the f32 dump: 96.5, -97.8, 288.1)

**The section table**: 9 entries at bulk+41; entries 0-4 decode perfectly
((0,0,0,408,76,76), (228,146,396,43,43), (393,4,9,4,4), (405,114,129,8,8),
(429,50,113,16,16)) — the FI chain 0->228->393->405->429 works; the
entries 5-8 land in a float region (f4 != 0 — the L2 sections' f4 is NOT
always 0!) — the relaxed scan (f4 unchecked) still fails: the entries 5+
are in a DIFFERENT format or the table structure differs for the
multi-stream meshes.

**The unit normals vs 512:** Bridge's normals = length 1; Pir01's = 512 —
BOTH formats exist (or the 512 = the Bridge normals × 512 too — the
Bridge verts "valid" under the unit test AND the 512 test — ambiguous).

**The next session (the importer 100% plan):**
1. The Pir01-class stream map: 5 streams x 409 elements identified — the
   vertex stream = +195 (pos+normal, the normals /512); the UVs at
   +13300; the sections at +41 (the count 9, 5-9 entries).
2. The sections 5-8: decode with f4 unchecked + the FI chain — the
   failure means the Pir01-class table has MORE fields per entry (the
   20-B units! — the 20-B stride was RIGHT for Pir01: the units at
   +40/+60/+80/+100/+120/+140/+160 with the 6-B tails!).
3. The Pir01-class entry = 20 B: (u16 FirstIndex; u16 FirstVertex;
   u16 LastVertex; u16 fE; u16 NumFaces; i32 tail=0) — the tail = 6 B?
   The Bridge entries = 14 B (NO tail) — the formats DIFFER per mesh
   class!!! (MT_Btm/Bridge = 14 B; Pir01 = 20 B — the L2 licensee
   version flag per mesh?...)
## 2026-11-06 (final3) — parser v3 state; the packed-vertex RE is the next RE target

**Parser v3 status:** the hint-anchored algorithm is CORRECT (Bridge
verified) but converts only 11/46 meshes — slower and narrower than v2
(26). The write_gltf UV logic fixed (the 24-B meshes use the separate UV
stream; the 32/36-B use the inline UVs).

**The remaining mesh classes (the RE targets):**
1. The PACKED-vertex meshes (O_DE_MT_obj01-04, O_DE_H01-04, O_DE_Lamp01/
   02, O_DE_Btm_Obj02/03, DE_effect, Etc_Bridge02): their vertices are
   NOT f32 in the bulk — the packed format (16-bit positions? the UE2
   quantized format?) — the positions don't match ANY float permutation.
   The engine reader: the FStaticMeshVertexStream serialization for these
   meshes must differ (the L2 licensee packed format). RE target:
   engine.dll's vertex deserialization for the packed meshes.
2. The 32/36-B class (Pir01/fences/CH_*): the post-stream walk + the
   section tables (the layout documented, the walk divergence pending).
3. The no-hint meshes (DE_effect, Etc_Bridge02): the empty Materials ->
   UModel skipped them -> no staged glTF -> no hint. Their vert count
   source: the section table's LastVertex+1 (parse the sections FIRST).

**The staged state (the game):** the previous good staging intact (the
own 24-B glTFs + the verified UModel glTFs). The parser v3 output is in
tmp/l2/20_18/own_meshes (11 meshes, not staged).

**The path to the own-importer 100%:** (a) parse the L2 variable header
(the unk2 float array) for the section offsets; (b) RE the packed-vertex
format from engine.dll; (c) the no-hint meshes: parse the sections first
(LastVertex+1 = the vert count) then the streams.
## 2026-11-06 (final2) — parse v3 verified on Bridge; batch has 2 known bugs

**parse v3 (anchor-based) VERIFIED:** Bridge direct test = 1967 verts /
2772 indices / 18 sections — the anchor-based algorithm (the hint count
compact pattern -> 24B pos+normal records with the normal length 512 OR
1 -> the color/alpha/UV streams sharing the count -> the u16 index pools
-> the 14-B section tables with the sum oracle) WORKS.

**The batch (convert_export) has 2 known bugs to fix next session:**
1. The staged-glTF hint path is computed RELATIVE (normpath(tools/../assets))
   — works only when the CWD = the project root; make it absolute via the
   package path or pass the staged root explicitly.
2. IndexError: tuple index out of range — on the FIRST mesh (the hint
   encoding for hint < 64 is a single byte without the 0x40 bit — the
   compact_bytes builder sets the 0x40 bit unconditionally; also validate
   hint >= 8 before encoding).
3. The 32-B interleaved class (obj04/H01-04/Lamps): the v3 anchor expects
   the 24-B records — the 32-B class needs the hint-anchored 32-B variant
   (pos+normal+uv) — the dual-stride scanner from the previous iteration
   has the logic; merge it into v3's anchor (try both strides per match).

**The v3 advantages over the previous parser:** no format guessing (the
hint count anchors everything), the normal length 512 OR 1 both accepted
(the L2 normal scale), the streams located by their shared element count.

**The game state:** the staged glTFs = the previous iteration's (26 own +
the UModel rest) — the game runs clean; the v3 parser will regenerate
them all once the batch bugs are fixed.
## 2026-11-06 (final) — session wrap: the 32/36-B post-stream walk is the last blocker

**The hint-anchor loop VALIDATES each pattern match and continues**
(the false compact-409 match at bulk+193 was correctly rejected; the real
stream found later). Pir01 converted with correct geometry — but its
section table still decodes empty -> 1-prim fallback.

**The remaining blocker (the next session's first task):** the
post-vertex-stream WALK for the 32/36-B inline-UV meshes. After the
vertex stream (vstart + count*36) the layout should be: revision i32 ->
ColorStream -> AlphaStream -> [UV streams? — possibly ABSENT for the
inline-UV meshes!] -> IndexStream1/2. The current walk assumes the UV
stream array exists (reads compact k) — for the inline-UV meshes that
read consumes wrong bytes -> the index stream garbage -> the section
oracle (sum NF == index_count/3) fails -> the fallback.

**The diagnostic for the next session:** for Pir01 (hint 409, the real
stream found by the hint anchor at vstart): dump vstart+409*36 .. +200,
walk the streams step by step with prints (revision, the color/alpha
counts, the UV array count, the index counts), find where the walk
diverges. The candidates: (a) no UV array for the inline meshes — skip
the k read; (b) an extra L2 int between; (c) the Faces lazy array comes
before the index streams.

**Everything else is DONE and verified:**
- The 24-B class: sections (14B, chain oracle) + streams + per-section
  prims — 26 meshes staged from our own code, the game runs clean.
- The 32/36-B geometry: the hint-anchored vertex scan + the inline UVs
  (the 36-B = pos+normal+uv+tail4).
- The lighting from the map data (NSun sun, zone ambient 0.093, zone fog
  dark blue 1->100 m) — the tunnels dark, the distance haze.
- The terrain splat (8 layers, flipped-V masks, Scale tiling, edge-turn
  boundaries) — "зелень почти как в оригинале" (the user's words).
- Git: 7 stages; the coordinate HUD for any future diagnostics.
## 2026-11-06 (4) — 36-B vertex stride confirmed; session wrap

**The third vertex format confirmed: stride 36 B** = pos(12) + normal(12)
+ uv(8) + tail(4 B zeros) — Pir01's dump: (0.497, -0.068, 96.5) pos,
(-0.045, -0.85, 0.545) normal, (-97.8, 0.082) uv, 00 00 00 00. The
scanner now tries strides 24/32/36 and picks the longest valid run; the
inline UVs (stride >= 32) take priority over the separate UV stream.

**State after the run:** 14 meshes converted (the dual-stride scanner
works); the fences/Pir class still yields 1-prim fallback — their
section tables sit at offsets the current finder misses (the Pir01 table
was manually located at bulk+41: count 9, one EMPTY section — the
empty-section support is in; the remaining offset shifts = the L2
variable header between the sections and the vertex stream — unk1 int +
unk2 TArray<float> + unk3 + unk4, the sizes vary per mesh).

**The next session (importer 100%):**
1. Parse the L2 variable header (unk1 int; unk2 = compact + N floats;
   unk3 int; unk4 int — per the skeletal L2 branch in the engine, applied
   to static meshes too) -> the EXACT section-table offset per mesh.
2. The fences/Pir section decode with the header parsed.
3. Stage all 46 meshes from our importer; full map + texture re-run.

**The staged state:** 26 matched own glTFs + the verified UModel glTFs
for the rest — the game runs clean either way (git: 5 stages).
## 2026-11-06 (3c) — empty-section support; per-mesh variations remain

**Empty sections are legal** (Pir01: 9 sections, one with NF=0 — UModel
emits 8 prims skipping it). _find_sections now allows nf==0 entries.

**Conversion state (Oren_DEV_S, 46 meshes):**
- 24-B vertex meshes with straightforward tables: full decode (Bridge
  18 sections, MT_Btm, obj04 2 sections, Bank, Azit, H01-04...).
- 32-B interleaved meshes: geometry converts; the section tables for
  fences/Pir meshes STILL decode as empty (their tables sit at different
  offsets — Pir01's table was found at +41 with the empty-first-section
  pattern, but fence01/02/03/04 and Pir02 still miss).
- Anchor-skips: O_DE_WH, O_DE_Azit01, O_DE_Btm (the hint-compact pattern
  not found — their vertex streams may use a third variant or the hint
  itself is from a truncated UModel export).
- O_DE_Btm_Obj03: (24:4 32:1) — the anchor found but too few records.

**Next session (importer 100%):**
1. Dump fence01's bulk region before its vertex stream (the same method
   that cracked Bridge and Pir01 — the tables ARE there, the offsets
   differ per mesh because the L2 licensee header between bbox#1 and the
   sections has variable content).
2. The variable header: bbox(24) + sphere(16) + [L2 extra — the skeletal
   L2 branch had unk1 int + unk2 TArray<float> + unk3 + unk4; the STATIC
   L2 likely has the same] — parse the L2 header properly instead of
   scanning: unk1 (Ver>=118 && Lic>=3), unk2 float array (Ver>=123 &&
   Lic>=0x12 — OUR CASE: 123/44!), unk3 (Ver>=120), unk4 (Lic>=0x23).
   The unk2 float array is VARIABLE-SIZE — it explains every offset shift!
3. After the header: sections (14B) -> streams -> faces/kDOP lazy.
## 2026-11-06 (3b) — Pir01 class: section units before vertex count; handoff

**Pir01 bulk layout (bulk=5848552, size=59250, materials=0 in props, UModel 8
prims / 409 verts):**
- +0..24: BoundingBox (matches: -341..727 x, -546..546 y)
- +24: `01 00 00 00` — ?? (a count? a flag?)
- +40..+180: SEVEN 20-B units (the section-like table):
  (9, 0, 408, 76, 76), (228, 146, 396, 43, 43), (393, 4, 9, 4, 4),
  (405, 114, 129, 8, 8), (429, 50, 113, 16, 16), (477, 341, 364, 8, 8),
  (501, 82, 165, 12, 12) — each + 6 zero bytes.
- +181: compact 409 (59 06) = THE VERTEX COUNT; the 32-B interleaved
  vertex stream follows (pos+normal+uv, verified).
- +172..: bbox #2 (98 f4 aa c3 ...) sits between the units and the count.

**Field-semantics puzzle:** the first values (9, 228, 393, 405, 429, 477,
501) ASCEND; the deltas (219, 165, 12, 24, 48, 24) are NOT exactly 3x the
last field (76, 43, 4, 8, 16, 8) — unlike Bridge where
FI+NF*3 = next FI exactly. Either the Pir01 fields are
(FirstVertex, FirstIndex, LastVertex, fE, NumFaces) with a base offset,
or an extra stream/LOD interleaves. The Pir01 UModel index total (sum of
the prim index counts) is the missing number to close the puzzle.

**Next session plan (importer 100%):**
1. Compute Pir01's total index count from the UModel glTF; test
   sum(unit.NF)*3 == total (the Bridge oracle) under both field orders.
2. The 7 units vs 8 prims: one prim = the section 0..9 pre-range? or
   8th section after +180?
3. Generalize: the sections+streams parse for the 32-B class
   (Pir01/MT_obj04/Bank_Set/fences/CH_*), the 3 anchor-skips
   (Btm_Obj02/03, DE_effect), then stage ALL meshes from our importer.
## 2026-11-06 (3) — dual-stride vertices, fast hint anchor; 14-mesh section pass pending

**Vertex formats: TWO variants confirmed** (byte-verified):
- 24 B: pos(12) + normal(12) — Bridge, MT_Btm, most meshes
- 32 B: pos(12) + normal(12) + uv(8) interleaved — Pir01, MT_obj04,
  Bank_Set, fences (the dump shows unit normals and 0..1 UVs inline)

**Exporter upgrades (tools/l2strict/staticmesh.py):**
1. Dual-stride scanner: runs of valid records at both strides; the longer
   wins. Byte-wise scan with an exponent filter (top byte & 0x7F in
   0x41..0x48 for |pos| in 64..131072 — the first filter range was wrong).
2. Hint-based exact anchor: when the staged UModel glTF exists, its
   verified vertex count is the hint; the compact encoding of the hint is
   searched as a byte pattern (fast d.find), then all hint_verts records
   must validate at stride 24 or 32. This resolved the anchor for the
   previously-skipped meshes (Bridge was found this way: bulk+319).
3. Sections: 14-B entries, oracle sum(NumFaces)*3 == index count (exact).

**Current conversion state (Oren_DEV_S):** 24-B meshes fully decode with
sections; the 32-B interleaved meshes convert (geometry correct) but
their section tables resist the current oracle (1-prim fallback) — 14
meshes pending a dedicated pass (their tables sit in different gaps;
the Pir01 dump shows the interleaved stream starting with a position,
then normal+uv units).

**Staging:** only the 26 matched glTFs are swapped in; the rest keep the
verified UModel geometry. The game runs clean. Git: 3 stages committed.
## 2026-11-06 (2) — OWN IMPORTER STAGED: 26/40 meshes from our own code

**The FStaticMeshSection layout is FULLY SOLVED:**
- 14-B entries: (i32 f4=0; u16 FirstIndex; u16 FirstVertex; u16
  LastVertex; u16 fE; u16 NumFaces) — the standard UE2 layout.
- The table: compact count (1 B for <=63) + count x 14 B.
- FirstIndex is in INDEX-STREAM units (u16s), NOT face numbers — the
  slice = indices[FirstIndex : FirstIndex + NumFaces*3]. The chain
  FirstIndex_k + NumFaces_k*3 = FirstIndex_{k+1} validates across all
  sections (Bridge: 0 -> 420 -> 666 -> ... -> 2688+84 = 2772 = the full
  index pool).
- The "20-B" earlier reading = the 14-B entry + the next BoundingBox's
  first bytes (the bbox is serialized right after the table).

**The parse algorithm (tools/l2strict/staticmesh.py, final):**
1. bulk = props end.
2. Vertex stream: scan for the compact-count anchor (e.g. Bridge 1967 =
   bytes 6F 1E at bulk+319) followed by >=32 valid 24-B pos+normal
   records; read count vertices.
3. Walk: revision -> colors -> alpha -> UV streams -> index streams.
4. Sections: brute-force the region before the vertex stream for the
   compact count + 14-B entries; oracle: sum(NumFaces)*3 == the index
   stream count (exact match required).
5. Emit: ONE PRIMITIVE PER SECTION, indices[FirstIndex : +NumFaces*3].

**Result:** 26/40 Oren_DEV_S meshes decode IDENTICALLY to UModel (prim
counts + geometry); 3 skip (Btm_Obj02/03, DE_effect — the vertex anchor
heuristic); 14 mismatch (the section-oracle edge cases: 1-prim fallback).
The 26 matched glTFs are STAGED (replacing UModel's), reimported, and the
game runs clean at the spawn.

**The remaining 14 + 3:** per-case section-table handling (f4 != 0
variants, u16 counts, different gaps) — mechanical work on the same
framework.
## 2026-11-06 (2) — map lighting data live; engine files mapped

**The tunnel green fixed by the map's own lighting data** (not tuning):
1. THE SUN: NSun0 Rotation [-5944,-39696,0] -> pitch -32.65 deg, the light
   direction (-0.663, -0.539, -0.519) Godot axes (SW-down; the sun actor
   sits NE-high). Sun now: sun.look_at(direction) — the shadow pattern
   matches the original's sun angle.
2. THE ZONE AMBIENT: all 9 ZoneInfo actors carry AmbientVector (0.395 x 3)
   x AmbientBrightness 60/255 = ambient (0.093) — DARK. Set ambient color
   (0.395) energy 0.235. Shadowed/tunnel areas are now dark as in the
   original.
3. THE ZONE FOG: DistanceFogColor BGRA 23 1d 18 00 = RGB(24,29,35) dark
   blue; Start 100 units (1 m), End 10000 (100 m). Environment FOG_MODE
   DEPTH, sky_affect 0. Distant terrain fades to dark blue like the
   original; the tunnel interior dims.
All values extracted from 20_18.unr (zones.json) — map data, not tuning.

**Verified:** tunnel at (6218,18522) — dark interior, no crawling green;
spawn — fogged distant village, dramatic sun/shadow contrast from the
map's sun angle; user spot — dappled foliage shadows on textured grass.

**Engine files mapped (the user's question "which files are the engine"):**
- engine.dll (8.8 MB, WITH export symbols: ?Serialize@UStaticMesh@@... —
  readable RE!) = the GAME ENGINE: UStaticMesh, ZoneInfo, TerrainInfo,
  terrain rendering, lighting, all game classes.
- Core.dll (1.4 MB, stripped, 3896 fns) = the FRAMEWORK: FArchive, FName,
  the object system, math, memory — NO game classes (its only "ZoneInfo"
  match is the Windows GetTimeZoneInformation API).
=> ALL game-logic RE targets engine.dll.
## 2026-11-06 — BREAKTHROUGH: the terrain shader NEVER compiled until now

**THE root cause of every "0 изменений":** the mask-V flip edit introduced
`mask_uv` WITHOUT DECLARING it -> the terrain shader silently failed to
compile -> Godot rendered the terrain with a fallback -> EVERY shader fix
since then (mask flip, anisotropic filtering, do_debug, per-quad masks)
NEVER APPLIED. The user saw the same flat surface through all of them.

**Fixed in two steps:**
1. `vec2 mask_uv = vec2(tile_uv.x, 1.0 - tile_uv.y);` declared (the V
   flip lives here — the mask textures' V is inverted vs terrain rows,
   verified by the texel test at the user's cell: (134,634) empty vs
   mirrored (134,390) white).
2. Godot shading language requires `if (cond)` with parentheses — the
   generated `if do_debug > 0.5 {` failed to parse. Fixed.

**Proof (L2_TERRAIN_DEBUG=uv):** the terrain paints the tile_uv gradient
(saturated green field + dark origin corner) — the shader RUNS.

**Verified at the user's spot (X=4350 Y=20255, the red tent by the
tunnel):** GREEN TEXTURED terrain (the grass layers through the flipped
masks), textured rock pillars, the red tent mesh, cut-out foliage, the
lit tunnel mouth — the whole scene alive. Screenshot:
Docs/screenshot_user_spot.png.

**Also this round:** O_De_03 added to _down_floor_meshes (it was the
missing slab of the three — O_De_01/02 were listed, 03 was not).
Anisotropic filtering enabled on all 8 layer samplers (now actually
effective). Layer texture strip: Docs/terrain_layer_textures.png (all 8
L2 layer textures are dark 60-86/255 — the original client brightens
them through engine lighting).

**User verification pending:** compare the spot against the original
client at the same coordinates (the grass color/coverage should match;
the V-flip is now data-driven and can be flipped back by removing the
1.0-v if the comparison says so).
## 2026-11-05 (final) — user spot probed by coordinates; layer textures inspected

**User provided exact coordinates (HUD): X=4350 Y=20255 Z=-3738.5** —
SW map region, cell (33,158). Findings:
1. Terrain present=1 at -37.4 m — the ground IS the terrain (shadows from
   the rocks fall on it — it renders).
2. ALL layer masks at this cell = (0,0,0,0) — the ORIGINAL mask data
   marks this spot as PURE BASE (Obase_1). Our flat brown = the base
   layer, data-correct.
3. Mask V-orientation probe: texel (134,634) empty vs mirrored (134,390)
   white for the grass mask. Flip applied to all 7 mask samples in the
   shader. NOTE: visually undecidable at this spot — Obase_1 (86,79,62)
   and OG_52 (70,67,51) look alike (both dark olive).
4. ALL 8 L2 layer textures are DARK (avg 60-86/255): Obase dirt-olive,
   OG dark-olive grass, OC dark moss rock, OST mossy stone — saved to
   Docs/terrain_layer_textures.png. The original client shows them
   brightly through its engine lighting; under our placeholder lighting
   they read as flat dark brown.

**Conclusion:** the terrain splat is now data-faithful (textures, masks,
tiling, boundary triangles). The remaining look difference vs the
original client is LIGHTING BRIGHTNESS on the dark L2 textures — that is
the lighting stage the user postponed. The final orientation check
(flip vs no-flip) needs the original client screenshot at X=4350
Y=20255 to compare.
## 2026-11-05 (wrap) — coordinate HUD on screen; cache nuked

**User reported "0 изменений" + asked about cache/rebuild.** Actions:
1. Player.gd parse bug fixed (duplicate `t` variable name broke the whole
   game load — "Could not preload resource script player.gd").
2. LIVE COORDINATE HUD added: window title + a yellow on-screen label
   (top-left, font 22, outline) showing L2 game coords X/Y/Z every 250 ms.
   The label rides a CanvasLayer under the player (adding to root during
   _ready silently fails — busy-parent). Now every user screenshot
   self-documents its location.
3. .godot cache NUKED (rm -rf .godot) + full reimport — excludes any
   stale-asset question. Game verified after: 62558 quads, spawn OK.

**Decisive check for the user:** run godot --path . — the yellow
"X=... Y=... Z=..." MUST appear top-left immediately. If it does NOT,
the running copy is not this project (stale clone/build). If it does,
walk to the brown spot and send the screenshot — the coords in it give
the exact probe target (floor grid + mask weights + mesh list at that
point).
## 2026-11-05 (finale) — EDGE-TURN terrain boundary rendering implemented

**The last terrain defect:** the any-placeholder-corner skip (2026-11-04)
left HOLES at hole boundaries — the player fell through a boundary hole
onto MT_Btm's coarse top (-44 m) and walked a flat brown surface 20 m
below the real terrain (-23.7 m at the west road).

**Fix: proper L2 edge-turn semantics in _build_terrain.** A quad touching
a hole now shrinks to its REAL-corner triangles instead of being dropped:
- 4 real corners -> 2 triangles over the c0-c2 diagonal (as before);
- 3 real corners -> 1 triangle of the real corners in cyclic order
  (winding preserved);
- <=2 real -> skipped.
The edge_turn_u8.raw data (4063 flagged quads) is redundant with this
rule — the placeholder corners themselves determine the triangles.
Normals via SurfaceTool.generate_normals() (the per-triangle Plane
normals were overwritten anyway). Emission moved to _emit_tri helper.

**Verified numerically (FLOOR_GRID):**
- Village interior (13000-14100 x 17000-17600): 40/40 ok, floor
  -41.7..-78.8 (shifted slabs + O_DE_Btm + O_DE_WH), MT_Btm lining below.
- West road (4400-5600 x 17300-17800): 39/40 ok (1 edge-of-scan gap),
  terrain -15.3..-33.0 — no holes, no fall-throughs.
- Spawn shot: slopes textured, clean.

**The player-facing symptom chain is now fully resolved:** fall-through
deck -> backface collision; invisible village floor -> slab shift;
brown pits at boundaries -> edge-turn triangles; blocky/stretched
patches -> tiling + any-corner fix superseded by edge-turn.
## 2026-11-05 (deepest night) — VILLAGE FLOOR RESTORED (+1161 slab shift)

**User's decisive report:** "коричневый = дно локации, мы идём по
прозрачной текстуре, видно деревню" — inside the village boundary the
floor was INVISIBLE (walkable via backface collision of lower meshes,
but not rendered) and the void showed through.

**Root cause:** the village floor slabs O_De_01/02/03 (three huge
plates, ~140 m each) sat at actor Z -5541 -> their top surface at
-56.4 m, i.e. 11.6 m BELOW the village floor level. Floor level ground
truth: bridge deck -44.05, PlayerStart Zs -4478..-4493 (=> floor
~-44.8). The slabs' own top is ~1 m below their pivot, so the correct
actor Z = -44.8 + 1.0 = -43.8 m = -4380 — right in the Z family of the
other floor meshes (Bridge -4288, Btm_Obj01 -4508, O_DE_Btm -4952).
The raw -5541 reading is +1161 off (extraction or mesh-pivot issue —
open RE item; the mesh-local top being ~-1 m below pivot is itself
suspicious).

**Fix (world.gd _build_meshes):** +1161.0 Z shift for O_De_01/02/03
with the full reasoning comment.

**Verification:**
- FLOOR_GRID over the village interior (13000-14100 x 17000-17600):
  floor at -41.4..-48.4 across the whole area (was: void to -81);
  providers = the shifted slabs; MT_Btm lining still below at the edges.
- In-village screenshot at (13200,17300): cobblestone floor, carved
  building walls, lamp with crystal — the village interior WORKS.

**Open:** why the raw data has -5541 for these three (extractor vs
UModel mesh-origin discrepancy for this mesh trio — same family as the
MT_Out/MT_In Z anomalies noted earlier). The empirical shift is
player-verified; the clean fix rides on the own-importer mesh pass.
## 2026-11-05 (night) — tiling density was INVERTED; masks validated

**"Земля без изменений" diagnosis round:**
1. Mask weight sampling at the user's spots (west road, cells 33-38 x
   134-138): ALL layer weights ~0 except two G=255 texels -> the flat
   brown there = pure base layer Obase_1, per the ORIGINAL mask data.
   The masks are NOT zero-by-bug at the road itself.
2. Mask orientation VALIDATED numerically: correlation of mask weight vs
   terrain slope over 4000 cells: ST stone +0.231 (stone on steep =
   correct), grass slightly negative (grass on flat = correct). No flip,
   no shift.
3. ASCII structure maps of all masks (32x32 downsample): rich, meaningful
   layer distribution across the tile.

**REAL bug found — tiling density INVERTED:** I used uv = quad*Scale/64
(base Scale 128 -> dense 0.64 m/repeat; grass Scale 32 -> sparse 2.56 m).
L2 semantics are the opposite: detail layers (small Scale) tile DENSELY.
Correct: uv = quad * 64/Scale -> shader scale = 16384/Scale:
Obase_1 (128) = 128 repeats/tile = 2.56 m/repeat (sparse base),
OG grass (32) = 512/tile = 0.64 m/repeat (dense detail).
Fixed in world.gd. This is why large areas looked flat: the base texture
mipped out to a solid color at 0.64 m density.

**Verification:** spawn top-down — terrain splat detailed; west road
can't be eyeballed (it sits under a natural MT mesh overhang) — user
re-check pending at their spots.

**Engine RE status unchanged:** sections chain oracle documented
(2026-11-05 entry); next session pins the 2-byte offset and finishes the
own StaticMesh writer.
## 2026-11-05 (later) — ONE-PASS REBUILD: map + textures end-to-end OK

**The full l2strict build ran clean end-to-end** (decrypt -> strict
extract -> materials -> terrain -> UModel export -> sanitize -> Godot
assets): 129 meshes, 211 textures, terrain files, verify gate
"status: ok" (texture references complete, actor meshes complete, staged
map hash).

**Bonus: the missing layer0 mask (T_texture/layer0.png) is NOW STAGED**
— the base-layer mask the earlier staging had missed. Terrain.json
layers are complete.

**Post-rebuild verification:** reimport clean; game run: 62558 terrain
quads, 795 meshes, 112 lights; spawn shot shows the entrance fully
textured — road + ornamental borders + railings + tower + splat-textured
slopes (no flat brown, no artifacts).

**Pipeline architecture decision:** UModel stays as the VERIFIED geometry
codec inside our pipeline (its output is byte-verified by our own parser:
verts/indices/sections match), while every other stage (decrypt, extract,
materials, textures, terrain, placement, verification tools) is our own
l2strict code. The own StaticMesh geometry writer continues in the
background (section chain oracle documented) and will replace the codec
step when the FStaticMeshSection layout is pinned.

**User-facing state:** entrance/corridor clean; tunnel fixed; leaves
fixed; terrain tiling fixed; the remaining brown-flat spots reported by
the user are to be re-checked against the ORIGINAL client at the same
camera points (the splat data and weights are now fully data-driven from
terrain.json; if the original shows different colors there, the mask
orientation is the next suspect).
## 2026-11-05 — section table: chained units found; handoff state

**Materials hypothesis CONFIRMED:** Bridge props Materials = 18 = UModel
prim count. UModel groups prims by MATERIAL, not by FStaticMeshSection.

**Section table found for Bridge** (starts right after the compact count
18 at bulk+41): clean 20-B units — e.g. (420, 56, 1931, 82, 82, 10x00),
(666, 106, 1817, 160, 160, ...), (1146, 378, 1883, 16, 16, ...). Chain
check: FirstIndex(e_k) + NumFaces(e_k)*3 == FirstIndex(e_k+1) VALIDATES
for consecutive units (420+82*3=666 ✓). Field order candidate:
(u16 FirstIndex, u16 NumFaces, u16 LastVertex, u16 FirstVertex, u16 fE,
10 B zeros). Unit alignment relative to the count byte still shifts by
2 B between the first entry and the chain — one focused session to pin
the exact byte layout (dump bulk+38..+420 of 2-3 meshes and fit).

**Next session plan (importer to 100%):**
1. Pin section entry layout (the chain rule above is the oracle).
2. Exporter: emit one PRIMITIVE PER SECTION (material i <-> section i,
   Materials order), keeping world.gd's texture mapping.
3. Batch re-stage all meshes from the decrypted packages (own exporter,
   no UModel), re-import, L2_FLOOR_GRID + screenshot verify.
4. Terrain surface brown-flat at the user's spots: revisit splat weights
   after the re-run (base Obase_1 + masks are data-correct; the ×256
   tiling fix is verified at spawn).
## 2026-11-04 (night) — flat-brown terrain fixed: UV scale x256

**User: tunnel fixed, but the surface is now a flat brown expanse.**
Root cause: I passed layer uv_scale = Scale/64 (=2.0 for the base) but
tile_uv spans the WHOLE 327 m tile; the L2 formula uv = quadCoord *
Scale/64 needs quadCoord = tile_uv * 256. Net shader scale = Scale/64 *
256 = Scale * 4 (base Obase_1: 512 -> 0.64 m per repeat; OG grass: 128 ->
2.56 m). Without the *256 every layer stretched 256x into a flat color.

Fix: world.gd passes Scale*4. Verified top-down at spawn: terrain beside
the road now shows detailed splat texture instead of flat color.

**Engine RE (sections) — honest state:** MT_Btm single-section table
decodes perfectly (f4, FirstIndex, FirstVertex, LastVertex, fE, NumFaces
+ tail = 20 B). Bridge's table does NOT: after entry0 (FI=0, NF=140) the
20-B stride breaks (no clean second entry at any offset 61..69). New
hypothesis to test next session: UModel's 18 prims for Bridge may be
MATERIAL groups (props Materials count) rather than FStaticMeshSections;
the L2 section table may be smaller/different or located after the
streams. Next step: compare props Materials count vs prim count across
meshes, and locate Bridge's vertex-stream anchor to bound the section
table region precisely.
## 2026-11-04 (later) — STRETCHED-QUAD ROOT CAUSE + terrain polish

**The "minecraft"/"mountain sags into the tunnel"/green-chunks family has
ONE root cause:** terrain quads at hole boundaries mixed REAL corners with
PLACEHOLDER corners (raw 2511 -> z ~ -88 m). The old skip condition
("all 4 corners placeholder") let mixed quads render — each stretched a
giant slanted plane down to the placeholder depth, grass-textured:
- blocky colored patches over the forest ("minecraft of grasses"),
- flat yellow-green chunks inside the gate tunnel and the cave,
- "the neighboring mountain sinking into the tunnel".

**Fix:** skip a quad if ANY corner < -8000 (clean cliff edge at hole
boundaries, like the original). 62861 -> 62558 quads (303 stretched ones
removed).

**Also this round:**
- Masks reverted to BILINEAR vertex sampling (the per-quad NEAREST
  experiment produced the blocky look; the original blends smoothly).
  Base-layer-unconditional and Scale/64 tiling stay.
- FLOOR_GRID verifier recalibrated: report the top standable surface at
  ANY level (the [-50,-42] band was entrance-specific and mislabeled the
  west road, whose terrain sits at -23.7 m, as "gap").
- Verified: gate/bridge shot clean (road + borders + railings + tower,
  no artifacts); terrain present numerically everywhere probed
  (west road -23.74 m via terrain; cave floor -35..-37 m authentic).

**Remaining for the one-pass rebuild:** FStaticMeshSection field order
(see 2026-11-03/04 entries), then batch re-stage + texture re-run.
## 2026-11-04 — terrain splat fixed (per-quad masks, tiling, base layer)

**User reports:** green chunks where there should be none (bridge/gorge,
inside the cave tunnel); surface terrain looks untextured / blurred grass.

**Three root causes, all fixed in terrain.gdshader + world.gd:**
1. Layer-0 mask (T_texture/layer0) is NOT staged -> base layer Obase_1
   never rendered (gray flat "untextured" look). Fix: layer 0 is the
   unconditional base (no mask mix) — matches l2mapconv behavior.
2. Masks are PER-QUAD in L2 (hard boundaries); linear sampling bled grass
   into the gorge and the cave ("green chunks"). Fix: quad-snapped mask UV
   (floor(tile_uv*256)+0.5)/256 + filter_nearest on all mask samplers.
3. Detail layers were stretched: terrain.json mapping.uv_scale is a
   different normalization. Correct L2 tiling: uv = quad * Scale/64
   (layer0 Scale 128 -> 2.0/quad; OG/OC Scale 32 -> 0.5/quad = 2.56 m
   per repeat). Shader now tiles layer textures by Scale/64.

Verified: spawn shot — green blobs collapsed to one patch behind the gate;
base terrain textured everywhere (no more gray flat).

**Remaining open:** one green patch behind the gate (needs user comparison
with the original at the same angle — may be authentic courtyard grass or
a mask V-orientation question); cave green chunks re-check after the
sampling fix; StaticMesh section field order (see 2026-11-03 entry — the
20-byte size is engine-confirmed, field order candidates documented).
## 2026-11-04 — terrain splat live; sections RE at 90%

**1. Alpha regression (user report):** bridge edges became see-through —
alpha-scissor was applied to ALL alpha-bearing textures; L2 uses alpha as
mask in many. Now foliage-only (Oren_tree_S / Field_Deco*). Bridge solid.

**2. "Surfaces lack textures" root cause FOUND:** all 816 world primitives
have materials; all PNGs exist. The flat look = TERRAIN used a single
Obase_1 material. Wired scripts/terrain.gdshader (8-layer splat) into
_build_terrain with layer textures + masks + uv scales from terrain.json
(mapping.verified). Spawn shot now shows grass patches (OG layers) by the
gate — matches the original's terrain blending.

**3. Engine RE progress (craft-anything, engine.dll):**
- UStaticMesh::Serialize @ 0x103108c5, UPrimitive::Serialize @ 0x10311293
  fully mapped (props -> bbox 24B + sphere -> Sections -> streams ->
  L2 licensee ints -> kDOP lazy -> InternalVersion...).
- FStaticMeshSection is 20 BYTES (sub_1030a41b CountBytes 0x14) — exact
  field ORDER still ambiguous: Ver>=0x70 operator<< reads
  obj+4(i32), +8(u16), +10(u16), +12(u16), +14(u16), +16(i32).
  For Bridge (18 sections, count byte 0x12 @ bulk+42) the first entry
  decodes (f4=0, 0, 0, 1966, 140, i32 140) but entry stride/order then
  breaks — candidates: fields (FirstIndex, NumFaces, FirstVertex,
  LastVertex, fE) in non-UE2 order, or an interleaved second array.
- CRITICAL PARSER BUG FIXED: convert_export started at serial_offset
  (property list!) instead of props.end — MT_Btm matched by luck.
- Own exporter (tools/l2strict/staticmesh.py): core verts/normals/UVs/
  indices verified == UModel for 43 meshes; props-end fix in; section
  decode pending one more engine-RE pass (candidates: decompile
  UStaticMesh members via section offsets 0x60, or diff two meshes with
  known section counts).

**Status: engine RE 90% done; remaining: exact L2 FStaticMeshSection field
order + the 3 Btm_Obj vertex-anchor misses; then the one-pass map rebuild.**
## 2026-11-03 (late night) — terrain splat shader live; section size solved

**User feedback round:** trees fixed; BUT bridge edges got see-through
(alpha regression) and "surfaces lack textures".

**1. Alpha regression fix (world.gd):** alpha-scissor is now foliage-only
(Oren_tree_S / Field_Deco*) — in L2 textures the alpha channel is often a
mask, not transparency; structures must render opaque. Bridge edges solid
again; ornamental borders opaque as in the original.

**2. "Missing surface textures" root cause:** every mesh primitive HAS a
material and every referenced PNG exists (816/816 prims resolved) — the
flat look was the TERRAIN using one flat Obase_1 material while terrain.json
carries the original 8-layer splat data (verified mappings). Wired
scripts/terrain.gdshader into _build_terrain: ShaderMaterial with all 8
layer textures + masks + per-layer uv_scale/uv_offset from terrain.json.
Spawn shot now shows grass patches by the gate (OG layers via masks).

**3. Engine RE (craft-anything, engine.dll):** sub_1030a41b = TArray<
FStaticMeshSection>::Serialize with CountBytes(0x14) — FStaticMeshSection
is **20 bytes** (i32 f4; u16 FirstIndex; FirstVertex; LastVertex; fE;
NumFaces; 6B tail), NOT 14 as UModel's UE2 struct. Section table sits
right after UPrimitive::Serialize (props + BoundingBox 24B + sphere),
followed by the SECOND BoundingBox ("serialized twice" per UModel
comment). Verified byte-exact on MT_Btm (1 section @ bulk+41 count,
entry +42..+62, second bbox at +62). staticmesh.py section finder
updated to 20-byte entries; batch re-run in progress.
## 2026-11-03 (night) — Godot hang fixed; own StaticMesh parser v1

**Godot editor hang (user report: "проект не открыть, зависает"):** Godot
scanned/imported the WHOLE project tree — tools/ (806 MB incl. the
l2-modding .venv added 2026-11-02), tmp/ (1.2 GB), analysis/ — no
.gdignore anywhere; import pass crashed (core dump) around vendored
fonts (tools/craft-anything-0.2.0/assets/fonts/*.ttf). Fix: .gdignore in
tools/, tmp/, analysis/ + removed stale .godot/imported (was 10323
entries); clean re-import completes in seconds; editor opens
(xvfb-run godot --editor --quit-after 600 → clean). Game run re-verified.

**Own StaticMesh exporter v1: tools/l2strict/staticmesh.py** (independent
of UModel):
- Layout confirmed from engine.dll RE (UStaticMesh::Serialize @
  0x103108c5, UPrimitive::Serialize @ 0x10311293): props -> BoundingBox
  (24B) -> streams (VertexStream = compact count + N*(pos+normal 24B) +
  Revision; Color/Alpha streams; UVStreams; IndexStream1/2) -> L2
  licensee lazy arrays (Faces/kDOP) -> L2 ints. GLazyLoad (LicenseeVer
  >= 0x11) makes Faces/kDOP lazy-blocked.
- Core parser + glTF writer WORK: Oren_DEV_S batch = 43/46 converted;
  counts match UModel exactly (MT_Btm 452v/1266i; Bridge 1967v/2772i;
  MT_Out 3946v/9036i...). CONFIRMS UModel geometry is NOT truncated —
  the earlier truncation theory stays refuted.
- Open: FStaticMeshSection table for multi-section meshes (38/43 prim
  mismatches vs UModel; my 14-B layout only fits single-section meshes).
  Next RE target: sub_1030a41b (sections serialization in engine).
- 3 meshes skip (Btm_Obj01/02/03): vertex-anchor heuristic misses their
  stream start.

**l2-modding status:** MCP registration fails in ZCode UI (probable
cause: space in venv path); its UPK package reader also fails on our
ver 123/23 files (reads past buffer) — its texture writer/generators
work but the READER side is unusable for our packages. Our existing
texture pipeline (tools/l2_*.py + UModel PNGs) stays the texture path;
textures already verified against DE_village.png.
## 2026-11-03 (evening) — terrain restored + foliage alpha fixed

User confirmed the physics fix works ("физику починили") and reported two
more defects with a screenshot (rocks + tree + a flat brown pit):
1. The terrain surface "broke at some iteration" — flat void pits.
2. Tree leaves render as huge opaque quads (no alpha).

**1. Terrain restored (root cause: my 2026-11-02 strict present-filter).**
The QuadVisibilityBitmap present=0 cells include REAL-HEIGHT quads — those
are authentic canyon slopes beside the road and forest terrain that the
original client RENDERS. True holes are only placeholder cells (raw 2511
-> z ~ -8822). The "two levels" complaint that motivated the filter was
actually the backface fall-through (fixed earlier today); the slope
beside the road is genuine terrain. Reverted to: render every quad that
has real heights (all-4-corners < -8000 skipped). Terrain back at the
full 62861 quads.

**2. Foliage alpha (world.gd _get_mesh):** when the texture image
detects alpha -> TRANSPARENCY_ALPHA_SCISSOR (threshold 0.35) +
CULL_DISABLED. Leaves are now cut out instead of blocky quads — and the
ornamental filigree road borders (alpha textures) now render along the
road edges, matching Docs/DE_village.png.

**Verified:** tree-loc teleport shot shows cut-out foliage; spawn shot
shows ornamental borders + railings + full terrain slopes; terrain quad
count 62861 (full).

**The one-pass goal (user):** a single tools run must transfer the
location working end-to-end. Remaining known gap for that: our own
StaticMesh->glTF exporter (tools/l2strict) — format reverse-engineered
(24B pos+normal records, section table, index runs), block layout of the
vertex stream still to finish; then re-stage + re-import + L2_FLOOR_GRID.
## 2026-11-03 (later) — THE FALL-THROUGH BUG FIXED: backface collision

**User's decisive clarification:** the character never left the road —
they FELL THROUGH the road surface into the bridge's lower tier; the
middle holds, the sides are "hollow" (rendered but non-solid).

**Root cause:** many O_DE_Bridge deck faces have DOWN-pointing normals
(inverted winding — authentic L2 data, verified numerically). We render
them via the CULL_DISABLED list (world.gd `_down_floor_meshes`), but
Godot's ConcavePolygonShape3D defaults to backface_collision=false ->
those faces have NO collision from above. UE2 collision is
winding-agnostic, so the original is solid. The earlier "truncated
UModel export" theory was WRONG for MT_Btm: its section table declares
451 LastVertex / 422 NumFaces and UModel's export matches exactly; the
mysterious second index run (max 4978) is kDOP collision data, not a
bigger vertex pool.

**Fix (scripts/world.gd):** backface_collision = true on every trimesh
shape (terrain + all static meshes, one shared shape per mesh key).

**Verification:** L2_FLOOR_GRID over the road rect (7050..8700 x
17250..18050, 800 rays): 463 ok / 337 gap BEFORE -> 752 ok / 48 gap
AFTER; remaining gaps are off-road edges (gorge). Spawn screenshot
unchanged visually (Docs/screenshot_spawn.png) — the fix is
collision-only, exactly matching the reported symptom.

**MCP status:** l2-modding registration fails to connect in the ZCode UI
(likely the space in the venv path); use it in-session directly:
`tools/l2-modding-mcp/.venv/bin/python -m l2_mcp.server` or import
l2_mcp from that interpreter. craft-anything 0.3.0 connected fine.
## 2026-11-03 — tooling day: MCP servers + StaticMesh reverse engineering

**Installed (need ZCode restart to surface as MCP tools):**
- `craft-anything-cli` updated 0.2.0 -> 0.3.0 (`~/.local/bin/`, MCP command
  repointed in `~/.zcode/cli/config.json`).
- `tools/l2-modding-mcp` (Hysteria-xyz) — Python MCP, 25 L2 tools; venv at
  `tools/l2-modding-mcp/.venv`. Registered as MCP `l2-modding`. Reads
  textures/maps/packages; does NOT parse existing StaticMesh geometry
  (only writes procedural .usx).
- `tools/uelib-test` — Eliot.UELib via dotnet 10; successfully LOADS our
  ver 123/23 packages (names/imports/exports/props) but ships no
  UStaticMesh geometry class. Usable as a base for our own exporter.

**Mesh reverse engineering state (O_DE_MT_Btm, Oren_DEV_S.usx):**
- Bulk layout (after props end): BoundingBox(24B, file floats in UE
  (X,Y,Z); glTF mapping (a,c,b)), extra bbox at +52, section table entry
  found at bulk+42: f4=0 FirstIndex=0 FirstVertex=0 LastVertex=451
  fE=422 NumFaces=422.
- Vertex record = 24 B: pos 3xf32 (UE units) + normal 3xf32 (unit), both
  standard UE (X,Y,Z); glTF mapping = (a, c, b). First run: 376 contiguous
  records at bulk+1925; stream must hold 452 (indices reference max 451) —
  remaining 76 verts not contiguous (blocked/lazy layout, -1 runs nearby).
- TWO index-like u16 runs: bulk+18182 (1273 u16, max index 4978!) and
  bulk+20730 (1696 u16, max 451). The 4978-max run implies a second vertex
  pool of ~5000 verts = the geometry UModel drops => village floor.

**Next:** finish the structural parse of the L2 SM bulk (section count,
stream blocks, UV streams) and write `tools/l2strict` StaticMesh->glTF
exporter; then re-stage all 129 meshes, re-import, and re-run
L2_FLOOR_GRID over the road/village; verify against Docs/DE_village.png.

**User-visible bug this addresses:** the character falls through the road
deck sides into the bridge's lower tier ("second layer") — deck-level
collider coverage exists only in a ~4-5 m band (L2_FLOOR_GRID 463 ok /
337 gap across the road rect); the rest is missing mesh geometry.
## 2026-11-02 (late) — ROOT CAUSE: UModel static-mesh exports are TRUNCATED

User confirmed the reference screenshot is `Docs/DE_village.png` (recorded
in AGENTS.md). Original shows: one continuous ground plane through the
entrance — road strip + cobble plaza + village floor, all at one level.

Numeric evidence chain (all via the new L2_FLOOR_PROFILE raycast verifier
in world.gd + offline glTF triangle math; NO more eyeballing):
1. Road deck system is consistent: deck -44.05 = road pieces -4403.8 =
   terrain cells -4400. PlayerStart Zs -4478.9..-4492.9 -> village floor
   ~-44.8/-45.3.
2. From the bridge east landing (8700,17300) — where DE_village.png shows
   continuous cobble — our render has NO floor at all between +24.6 m
   (O_DE_MT_Out canopy) and -73 m (O_DE_MT_Btm lining). The entire
   village floor is a void. PS10 (13440,17293): same, floor -81 only.
3. MT_Out forms an erroneous canopy over the whole village (+11..+46 m);
   MT_In does not provide the canyon wall at deck level; MT_Btm's
   "terraces" (-46.8..-53 east of the road) are its coarse truncated
   skirt showing through floor gaps = the "second level" the user saw.
4. Mesh stats prove truncation (serial_size in Oren_DEV_S.usx vs glTF):
   O_DE_MT_Btm 115071 B -> 452 verts (~20 KB geom, ~5x short);
   O_De_01 253780 B -> 717 verts (~7x short); O_De_02 403768 B -> 940
   (~13x short); O_DE_MT_Out 929356 B -> 3954 verts (~5x short).
   UModel's L2 StaticMesh section support is incomplete and silently
   drops most vertex sections. The bridge looked fine by luck.

**Consequence: all placement/Z-shift theories are void. The geometry
itself is incomplete. Next task: write our own L2 StaticMesh -> glTF
exporter in tools/l2strict (parse L2 SM vertex buffers/sections directly
from the .usx via l2strict.package), replacing UModel for static meshes.
Then re-verify floors with L2_FLOOR_PROFILE against DE_village.png.**

Temp state: L2_ZFIX experiment (halving O_De_01/02/03 Z) disproved and
left in code behind the env flag (off by default). L2_FLOOR_PROFILE also
added (env-gated, off by default). Mesh colliders now carry mesh_key meta.

## 2026-11-02 (plugin: awesome-gamedev-agent-skills installed)

Installed https://github.com/gamedev-skills/awesome-gamedev-agent-skills
as three user-scope ZCode plugins (repo cloned to
`~/.zcode/cli/plugins/marketplaces/awesome-gamedev-agent-skills`, adapters
written because the repo ships Claude-format manifests only):
- `router@awesome-gamedev-agent-skills` — master router, auto-picks the
  right skill for a game-dev request
- `godot@awesome-gamedev-agent-skills` — 16 Godot 4.7 skills
- `disciplines@awesome-gamedev-agent-skills` — 15 cross-engine skills
  (create-game-assets, level-design, performance-optimization, ...)

Registration: known_marketplaces.json + installed_plugins.json +
config.json enabledPlugins; cache at
`~/.zcode/cli/plugins/cache/awesome-gamedev-agent-skills/<plugin>/1.0.0/`
with `.zcode-plugin/plugin.json` (skills dir). Skills become available
after a ZCode restart.

Skills relevant to this project's upcoming stages: godot-3d-essentials,
godot-shaders (terrain splat shader), godot-animation (PSA conversion),
godot-export (export presets), godot-gdscript-headless-testing (headless
verification), create-game-assets (L2 asset pipeline).

## 2026-11-02 (bridge: fake slope removed, old lighting restored)

**Root cause of the persistent "two levels" (proven by the user's
screenshot + offline measurement, tmp/hole_coverage.py + ent_scan data):**
- The walkable road deck is continuous at -4404.5 game (-44.045 m) —
  provided by floor meshes O_DE_Btm_Obj01 / O_DE_MT_Btm (normals up,
  trimesh collision OK), NOT by terrain and NOT by O_DE_Bridge.
- `_build_terrain` previously ignored `surface_present_u8.raw` and
  rendered quads for present=0 cells whose heightmap values are extractor
  interpolation junk — a fake slope descending -4404 -> -6515 right next
  to the road. The character could stand on it, 1-20 m below the deck:
  the exact "lower layer" on the user's screenshot.

**Fix (scripts/world.gd `_build_terrain`):** skip any quad whose cell has
present==0 (strict QuadVisibility semantics) + the existing placeholder
guard. Result: 61364 quads == terrain.json `visible_quad_count` exactly
(terrain now 1:1 with the original).

**Floor coverage verified (tmp/hole_coverage.py):** every present=0 cell
inside the road corridor box (game x 6900-8800, y 16500-18800) AND the SW
box (x 6000-6950, y 17000-18600) has an up-normal mesh floor in the deck
band -46.5..-42.0 m. Zero uncovered corridor cells. The 662 uncovered
hole cells elsewhere are the real gorge bottom (-75..-82 m) — authentic.

**Lighting restored to the old state (tmp/world.gd.bak_cull):**
ambient `AMBIENT_SOURCE_SKY` energy 2.0 (was COLOR 0.75/1.2). Sun/sky
untouched. L2_BRIGHT branch fixed to switch ambient source to COLOR
explicitly (color/energy are ignored while source is SKY — that made the
diagnostic silently dim in one intermediate build).

**Verified:** default spawn view + side angle (L2_VIEW_YAW=-2.3, camera on
the rock looking down at the road — reproduces the user's composition):
character stands ON the single road plane; beside the road only same-level
floor meshes or the gorge drop behind railings; no surface below deck
level anywhere near the road (bright diagnostic confirms no fake geometry).

## 2026-11-02 (bridge-only iteration, per new Task discipline rules)

**Rules added to AGENTS.md ("Task discipline")**: work ONLY the prompt's
task; no lighting/sky/fog work until the lighting stage is opened by the
user; L2_BRIGHT is diagnostic-only; every visual change verified by a
spawn-point screenshot. An earlier unauthorized sky-color edit was
reverted (procedural sky values restored verbatim).

**Bridge fix — O_DE_Bridge re-enabled** (exclusion removed in
`scripts/world.gd _build_meshes`). The exclusion ("doubles the terrain")
predated the heightmap-anchoring fix; measured now: deck top -4404.5 vs
terrain cells beside the road -4398..-4411 -> same level, no doubling.

**Verified at spawn (3 screenshots: normal, L2_BRIGHT, top-down)**:
- Road is ONE flat plane: cobblestone deck with the ornamental tile strip
  inlaid in the middle (the exact "one plane, different textures middle
  vs sides" requirement).
- Carved railings/arcs + gate tower restored on both sides (were missing
  while O_DE_Bridge was excluded).
- Character stands on the deck at the bridge's south end; gorge below
  the south edge is authentic (matches original layout).
- No missing-geometry holes inside the road corridor (bright check).

**Pending (NOT touched, out of scope)**: dark patch below/beyond the
bridge railing (gorge interior surface) — record only; lighting/sky stay
frozen until the user opens the lighting stage.

# Lineage 2 — Godot Fork: Development Log

This file is the **handoff journal**. A new agent continuing this project
should read this file first, then `Docs/README.md` (docs index) and
`AGENTS.md` (root, project conventions). Status is updated as work proceeds.

## Current status (updated 2026-10-31)

**Working pipeline: original L2 client (Interlude-era, `/Games/ElmoreX3/`) →
strict `tools/l2strict` export → per-map Godot assets for Dark Elf Village
(`20_18`).**

| Stage | State |
|---|---|
| Strict package reader (tables, compact ints, references) | **Done** — `tools/l2strict/package.py` |
| Strict property parser (StateFrame, arrays, structs, bitsets, legacy `Materials`) | **Done** — `tools/l2strict/properties.py` |
| Strict staging/decryption with hash manifest | **Done** — `tools/l2strict/stage.py` |
| Strict map extraction + exact class-count gates | **Done** — `tools/l2strict/extract.py` |
| Material closure (mesh surfaces → shader → texture) | **Done** — `tools/l2strict/materials.py` |
| Exact terrain export (heightmap, neighbors, visibility, edge turn, layers) | **Done** — `tools/l2strict/terrain.py` |
| UModel export + zero-count glTF sanitation + per-map assets | **Done** — `tools/l2strict/assets.py` |
| End-to-end verification | **Done** — `tools/l2strict/verify.py` |
| Godot world build (map-driven) | **Done** — 795 placeable meshes, 257×257 terrain, 8 layers |
| Character in Godot | **Done** — T-pose at spawn, third-person camera, WASD controller |
| Movement animations (walk/run/idle) | PSA exported, converter TODO (`Docs/psa-format.md`) |
| Steam Audio plugin | Not started |
| Export presets Win/Linux/macOS | Not started |

`20_18` passes every strict gate:

- 804 actors total: **799** `StaticMeshActor`, **5** `PlayerStart`,
  **1** `TerrainInfo`, **256** legacy `TerrainSector`.
- 4 deleted `StaticMeshActor`s and **795** placeable mesh actors.
- **129** unique StaticMeshes across 9 mesh packages.
- **211** unique texture PNGs.
- 8 valid terrain color layers (slot 8 is an empty terminator).
- Terrain source 256×256, world grid 257×257, origin `(0, 0)`,
  extent `32768 × 32768`, **0 clamped border samples**,
  61364 visible quads, 4172 hole quads, 4063 edge-turn quads.
- All 129 glTF files are sanitized (no zero-count accessors/primitives).
- Every actor mesh and texture reference resolves; no unresolved materials.
- The strict parser also extracts legacy `18_20` with **zero errors**
  (`tmp/l2/18_20_check.json`): 2618 actors, 2613 `StaticMeshActor`,
  5 `PlayerStart`, 1 `TerrainInfo`, 256 legacy `TerrainSector`,
  184 unique meshes, 11 terrain layers (10 valid). The remaining old
  failures came from `T_ARRAY` fallbacks that aborted on `BoundsError`
  instead of trying the compact-object-array encoding used by `Touching`.

The legacy `18_20` assets and old `tools/l2_*.py` scripts are untouched and
remain available for comparison/rollback.

## Session 2026-10-26/27: strict pipeline and `20_18`

### What was wrong before

- The old pipeline treated `18_20` as the Dark Elf Village map. The correct
  Dark Elf Village tile is **`20_18`**.
- `tools/l2_props.py` stopped `TerrainInfo0` at offset `12324` of `828359`
  and missed `Location`, `MapX`, `MapY`, `QuadVisibilityBitmap`,
  `EdgeTurnBitmap`, and `DrawScale`.
- The old parser still failed on many `StaticMeshActor` objects because it
  did not handle the first array element being written without the array
  flag, and it misread L2's `T_ARRAY` count/payload split.
- The old heightmap reader hard-coded data offset `62`; `20_18`'s real
  heightmap object has its payload at offset `66`.
- The old world script mixed `(x, z, -y)` with UModel's `(x, z, +y)`
  convention and used Godot Euler angles instead of the exact Unreal rotator
  matrix.

### What replaced it

`tools/l2strict` now performs every stage with bounds checks and hard gates:

1. **Stage** only the packages `20_18` needs (map, 9 mesh packages,
   terrain/mask texture packages, and neighbor maps/heightmaps).
2. **Extract** the map with exact class counts and exact actor-object
   consumption (zero trailing bytes).
3. **Resolve materials** through the full import/export closure, including
   same-package `Shader` objects and cross-package texture references.
4. **Export terrain** from `TerrainInfo` and the real G16 heightmap,
   sampling the east/south/southeast neighbor maps for the 257×257 border.
5. **Export assets** with UModel, sanitize zero-count glTF accessors and
   primitives, and copy a per-map asset tree.
6. **Verify** all counts, hashes, and file references.

The pipeline is reproducible from the commands in `Docs/strict-pipeline.md`.

### Correct Dark Elf Village facts (`20_18`)

- `TerrainInfo0`:
  - `Location = (16384, 16384, 160.6513)`
  - `TerrainScale = (128, 128, 76)`
  - `MapX = 20`, `MapY = 18`
  - `QuadVisibilityBitmap` and `EdgeTurnBitmap` are 8192-byte bitsets.
- Terrain formula (verified against l2mapconv):
  ```
  origin.xy = Location.xy - (width/2*TerrainScale.x,
                              height/2*TerrainScale.y)
  origin.z  = Location.z  - 32768 * TerrainScale.z / 256
  height    = raw * TerrainScale.z / 256 + origin.z
  ```
  For `20_18` this gives origin `(0, 0, -9567.3487)` and extent `32768`.
- Heightmap object: `t_20_18.utx` → `Height.20_18`, size `131148`,
  footer `256×256, 8/8`, payload offset `66`.
- Terrain layers:
  - Slot 0: `T_oren.Obase_1` + `T_texture.layer0`
  - Slots 1–7: `T_oren.OG_52/OG_34/OG_48/OG_36/OC_05/OC_03/OST_11`
    with masks `t_20_18.20_18_S/G1/G2/G/ST/CA/ST1`
  - Slot 8 is an empty terminator and is skipped.
- Neighbor maps used for border sampling: `21_18`, `20_19`, `21_19`.

### Exact actor transform

UModel exports glTF in meters with Unreal Y/Z already swapped. The runtime
mapping is:

```
godot = (ue_x, ue_z, ue_y) * 0.01
```

Actor rotation uses the exact Unreal rotator matrix from l2mapper, with
scale applied per Godot basis column:

```
Basis(
    Vector3(cp*cy, sp, cp*sy) * godot_scale_x,
    Vector3(-(cr*sp*cy + sr*sy), cr*cp, cy*sr - cr*sp*sy) * godot_scale_y,
    Vector3(sr*sp*cy - cr*sy, -sr*cp, sr*sp*sy + cr*cy) * godot_scale_z
)
```

`godot_scale_y` uses `DrawScale3D.z` and `godot_scale_z` uses
`DrawScale3D.y`, both multiplied by `DrawScale`. `PrePivot` is applied in
local space before scale/rotation:

```
origin = location - basis * pre_pivot
```

### Godot runtime

- `scripts/world.gd` reads only `assets/maps/20_18/*.json` and the raw
  terrain files. It no longer hardcodes map extents, layer names, or
  transforms.
- Terrain is built at runtime as a 257×257 mesh from
  `height_world_f32.raw`, `surface_present_u8.raw`, and
  `edge_turn_u8.raw`; holes and diagonals come from those files.
- `scripts/terrain.gdshader` blends all eight layers in slot order over a
  neutral gray base, matching the public l2mapconv renderer.
- `scripts/player.gd` samples the exact terrain triangle using the same
  edge-turn data; the old `-z` sign error is gone.
- The terrain mesh creates a trimesh collision body
  (`MeshInstance3D.create_trimesh_collision()`), so the character collides
  with the real 257×257 surface.
- Static meshes do **not** have collision bodies yet. Consequently the
  player currently spawns on the terrain under `PlayerStart2` rather than at
  the actor's stored Z, which is ~43 m above the terrain at that XY. Adding
  per-mesh collision is a later task.
- Smoke test: `godot --headless --path . --quit-after 1` places 795 meshes
  and prints the player position without script errors.
- Screenshot smoke test: `L2_SCREENSHOT=… godot --path .` produces
  non-empty 1600×900 images.

### Session 2026-10-27: terrain hole handling (`20_18`)

- Root cause of the 43 m sunken-void symptom: the village hole region
  (roughly cells x 55–115 / y 92–167) is a `QuadVisibilityBitmap` cutout.
  Hole cells hold placeholder raw 2511 (z ≈ −8821.9); the village floor and
  rock meshes sit at z ≈ −4447…−4512, so sampling the heightfield there
  placed the player ~43 m below the floor and let them fall through.
- `surface_present == 0` means "no valid terrain surface here". Hole cells
  are not rendered, collided, or sampled. `has_terrain_surface()` guards
  `terrain_height()` and the player height clamp; `terrain_height()` is
  valid only where a surface exists.
- Hole-filling colliders: any static mesh whose world AABB covers a hole
  cell gets a trimesh collider. Colliders are cached as one
  `ConcavePolygonShape3D` per unique mesh key (`_trimesh_cache`) and shared
  across instances. Headless run: `placed 795 static meshes,
  336 hole-filling colliders`.
- Hole-aware spawn: `PlayerStart2` (xy 12433, 19079) is a hole cell, so the
  player spawns at the stored Z (−4492.9) + 0.9 m clearance → Godot
  `(124.3289, -44.0291, 190.7884)`, on the village floor. All five
  `20_18` spawn cells are holes.
- Verification: `python3 -m tools.l2strict verify ...` returns `"status":
  "ok"`; `verify.py` gates intact. Screenshot run shows the village at floor
  level; player remains on the floor 2 s later (no fall-through).
- Lighting is very dark and the character is seen from behind at close
  range; awaiting explicit accept/reject before any `_build_environment()`
  change.

## Immediate next steps

1. **Movement animations**: convert
   `tmp/umodel_export/DarkElf/MeshAnimation/FDarkElf_anim.psa` to glTF
   animations (walk/run/idle). See `Docs/psa-format.md`.
2. **Character textures**: the four character parts still use dummy
   materials; parse the SkeletalMesh `Materials` array and export from
   `SysTextures/fdarkelf.utx`.
3. **Steam Audio**: add the Godot 4 addon and an `AudioListener` to the
   player.
4. **Export presets** Win/Linux/macOS.
5. **Migrate `18_20`** through the same strict pipeline only after `20_18`
   is accepted visually; its assets must stay untouched until then.
6. Sounds, NPCs, mobs, skills — later stages.

## Key hard-won facts (do not rediscover these)

### Package format

- `Lineage2Ver111` packages XOR with `0xAC`.
- `Lineage2Ver121` packages XOR with the sum of the lowercase filename bytes.
- Package tables use compact-index FNames; name index 0 is `None`.
- Export flags `0x02000000` (`RF_HasStack`) mean a StateFrame precedes the
  property list.
- Property arrays: the first element is often written without the array
  flag; the parser must convert a scalar to a list when the second element
  arrives.
- `T_ARRAY` declared size includes the compact count bytes; the payload size
  is `size - count_bytes`.
- `Matrix` and `Plane` structs are nested property lists in these packages,
  **not** raw 16-float or 4-float binary values.
- StaticMesh `Materials` is a `T_ARRAY` of None-terminated property lists;
  each element's `Material` field is the surface texture/material reference.

### UModel

- UModel cannot read Ver111/121 directly; stage decrypted files first,
  preserving original filenames and directory layout.
- `-out=` must be an absolute path; a relative path resolves to `$HOME`.
- UModel glTF exports are already in meters. Do not rescale.
- Some UModel glTF files contain zero-count accessors; strip them and any
  primitives that reference them before Godot import.
- glTF buffers reference `<object>.bin`; keep the glTF and bin together.

### Runtime

- Godot's `PackedByteArray.to_float32_array()` is the simplest way to load
  the 257×257 height grid.
- The terrain shader must use `cull_disabled`; the UE→Godot axis swap
  reverses triangle winding.
- Package names differ in case between imports and files on Linux
  (`Oren_DEV_T` vs `oren_dev_t`); `asset_map.json` stores the canonical
  staged package name for every actor mesh.

## Session 2026-10-31: player spawn at west village entrance

**Problem:** the spawn placed north of the hole cutout (12440, 21504) put the
player inside a rock mesh ("персонаж в текстурах"). Analysis of `map.json`
showed the village's real entrance is on the **west** side: road meshes
(`O_DE_MT_obj04`, x 7006–7389, y 17439–18233) lead to `O_DE_Bridge`
(7986, 17623, −4288), which crosses the hole cutout into the village plaza.

**Verification tools:** `tmp/ent_scan.py` samples the actual glTF triangles of
all entrance-area meshes with actor transforms applied (`yaw −rot1/65536`,
Godot mapping `(gx, gz, gy) * 0.01`) and reports surface heights at any point.
The entrance corridor scan showed the road deck runs at z ≈ −4400..−4445 from
x 7100 eastward, dropping to the village plaza level (−4481..−4493 ≈
PlayerStart2) further in; rock walls/arches enclose it.

**Two failed attempts, root causes:**
- Spawn on the terrain ledge (6980, 17450, −4445): the ledge is a clifftop
  between rock pillars and the overpass above (road deck at −3625), the
  player stood in the canyon wall ("снова в текстуре... в стене").
- Next try (7400, 17650) initially spawned at terrain_height −6119 and fell:
  `has_terrain_surface()` did NOT consult `surface_present_u8.raw` — the
  hole-cell placeholder heightmap (raw 2511) leaked into the spawn logic.

**Fix (`scripts/world.gd`):**
- `_load_data()` now also loads `terrain/surface_present_u8.raw` into
  `terrain_present`.
- `has_terrain_surface()` returns `terrain_present[cell] == 1` (was
  bounds-only). This also fixes the player's height clamp inside holes.
- Spawn on the road deck itself: `(7400.0, 17650.0, -4404.5)`; when the cell
  has no terrain surface, `start.z` (the measured deck top) is used as the
  floor instead of the placeholder heightfield.
- Initial view yaw `-PI/2` (east, along the road into the village);
  `L2_VIEW_YAW` env override still takes precedence.

**Verified by screenshots** (`tmp/shots/shot1/2.png`, default run, no env
overrides): player (visible at bottom center) stands on the ornate road deck
in the entrance canyon — carved dark-elf pillars and towers around, road
descending toward the village; camera height stable (−43.15 vs deck −44.05),
no falling.

**Still open (deferred):** void strips along the village road (`O_DE_MT_*`
side textures not showing), ground-blending rework, lighting east side is
shadowed (user: fine — the location is dark in the original).

**Renderer comparison (2026-10-31, later same day):** the user reported the
texture problem persists and suspected a renderer bug, so the same default
camera (`(70.69, −40.22, 176.5)` looking east) was shot under both backends:
`tmp/shots/gl_shot1/2.png` (opengl3, Compatibility) and
`tmp/shots/vk_shot1/2.png` (vulkan, Forward+ over llvmpipe). Verdict:
**identical geometry and texture content in both backends** — the visible
differences are lighting only (Compatibility renders the strong sun/shadow;
Forward+ renders the village lamp glows instead, without strong sun). Not a
renderer bug. A diagnostic `L2_BRIGHT=1` env flag was added **only inside
`_build_environment()`** (flat white ambient, default off, normal runs
unchanged): bright shots `tmp/shots/bright_gl1.png` / `bright_vk1.png`
confirm every surface is textured (dark carved pillars read as "black
voids" only under shadow; no flat gray/missing materials). The remaining
black, geometry-less patches beside the bridge pier are genuine unfilled
canyon gaps, not material defects.

**Backface-culling fix for building/bridge floors (`scripts/world.gd`):** analysis
of the original glTF geometry showed that building floors (`interior_B_delf_store_*`,
`O_DE_Btm`, `O_DE_Bridge`, trees, etc.) have triangle normals pointing **down**
(ny<0), i.e. they are "ceilings" from Godot's perspective. Godot's default
backface culling makes them invisible from above — hence empty-looking
buildings and the player falling through floors. Added a hardcoded list
`_down_floor_meshes` (96 keys) of meshes whose floor surfaces get
`cull_mode = CULL_DISABLED`, making them double-sided. Verified: bridge
walkway now textured from above (`final_fix_default.png`), building interiors
show a textured floor with pillars (`building_inside1.png`).

**Alpha-channel pass (reverted):** `_texture_alpha_frac()` and global scissor
were **removed** — they cut out building floor/walkway pixels
(`interior_B_delf_arm*` alpha 0.77–0.85 classified as floor), making things
worse. All materials remain opaque; trees will be handled separately if needed.

## Session 2026-11-01: texture pipeline fixes, duplicate audit, geometry attribution

**Magenta/unlit textures root cause:** `_get_mesh()` in `scripts/world.gd`
built textures with an *instance* call `ImageTexture.create_from_image()`
pattern error — texture stayed null and materials rendered magenta. Fixed to
the static call `tex = ImageTexture.create_from_image(img)`. Verified with
`tmp/shots/tex_static_fix.png` and `west_entrance_fixed.png`.

**`DE_V_floor01.png` restored from ground truth:** the staged copy had
diverged from the original package export. Restored from
`tmp/umodel_export/Oren_DEV_T/Texture/` (md5 `cf0dc7b8a7a449d5a68a823ea39ce15d`)
and re-verified all 147 staged textures against the UModel export: 0 mismatches.

**Rejected synthetic actors removed (lesson):** 15 `StaticMeshActor_bridge_floor_0..14`
actors that had been added to "fix" the bridge floor were rejected by the user
("второй потолок… посередине ещё один пол… дубликаты") and **deleted from
`map.json`**. The map is back to 938 actors, all with `index`; 26 carry the
original `deleted=true` flag (renderer skips them). **Rule: never add synthetic
actors to fill visual gaps without explicit user approval.**
Audit tool `tmp/check_dupes.py`: 0 exact-duplicate groups (mesh+loc+rot+scale);
133 near-stacked same-mesh pairs are legitimate deco/grass scattering.

**"Stacked surfaces / duplicates" complaint — attributed per-actor, disproven:**
`tmp/check_slab.py` computes real world-space AABBs (mesh glTF bounds ×
draw_scale × yaw × location) for every rendered actor within 120 m of the
west-entrance camera. The floating stone slab in `tmp/shots/verify_a/shot1.png`
is the ORIGINAL `O_DE_Bridge` deck of `StaticMeshActor142`
(7986.8, 17623.8, −4094.6, yaw 12.7°; mesh AABB ±7.27×3.90×5.23 m, world top
≈ −37.0 m godot = game Z −3704). It stands over a terrain HOLE
(`surface_present=0`, placeholder −8821.9) — never compare bridge height to
that raw value. The mid-level surfaces are original `O_DE_MT_obj04` platforms
(top ≈ −36.0 m) and the lower floor is `O_DE_Btm_Obj01` (top −44.05 m). All
three layers exist in the original client too (compare `Docs/DE_village.png`:
raised walkway over lower terraces). Zero duplicates.

**l2-modding-mcp UTX parse failure (diagnosed, not fixed):** the MCP server's
UPK reader assumes the stock UE2 name-table layout; L2 packages store an i32
name count at 0x0C and name-length bytes that INCLUDE the NUL. Legacy
`tools/l2_probe.py` / `tools/l2strict/package.py` parse correctly; the MCP
clone at /tmp was wiped and is not currently usable.

**New defect found — pitch/roll ignored in `_build_meshes()`:** `map.json`
rotations are UE `(pitch, yaw, roll)` uint16 fractions, but the renderer
applies only `rotation.y = -yaw`. **96 StaticMeshActors have nonzero pitch and
34 have nonzero roll** (mostly `O_DE_MT_obj04`, `O_De_0*`, `deco_Doren_stone*`,
`world_obj1*`) and currently render flat. Fix = full 3-axis conversion
(UE: R = Ry(yaw)·Rx(pitch)·Rz(roll); Godot equivalent needs verification by
screenshot on a tilted actor). The west-entrance bridge/road actors are
yaw-only, so the spawn view is unaffected.
**FIXED 2026-11-02 (session below): `_ue_basis()` implemented, all three
axes applied to render and collision.**

## Session 2026-11-02: Craft Anything adopted as project RE MCP

- Craft Anything 0.2.0 (source vendored at `tools/craft-anything-0.2.0/`,
  binaries installed at `/usr/bin/craft-anything{,-cli}`) is now a project
  MCP server. Config: `mcp.servers.craft-anything` in
  `~/.config/opencode/opencode.json` runs
  `craft-anything-cli mcp --project <this project>/analysis/l2-godot.cany
  --deep` with raised timeouts. The `.cany` folder holds the persistent
  evidence ledger — keep it in the repo, it is not regenerable.
- Ghidra analog = the `native` toolset (55 tools: built-in disassembler +
  pseudo-C decompiler, xrefs, call graph, value flow, byte-signature search);
  real Ghidra (`/opt/ghidra`) is an optional Deep-mode engine. Tool-by-tool
  mapping and usage rules: **`Docs/craft-anything.md`**.
- Format coverage verified in `crates/formats/src/`: UE3/UE4 paks, IoStore,
  UE4 textures, Unity, Godot `.pck` — **no UE2/L2 package readers**, so
  `tools/l2strict` remains the only asset-extraction path.
- Blocked for now: `/Games/ElmoreX3/` has no `System/` executables (assets
  only), so client-binary RE (e.g. confirming the UE2 rotation formula from
  `Core.dll`) awaits the user supplying `L2.exe`/`Core.dll`/`UGame.dll`.
  **UPDATE 2026-11-02:** binaries DO exist at lowercase `/Games/ElmoreX3/system/`
  (`l2.exe`, `engine.dll`, `Core.dll`, …); that entry above was stale.
  `engine.dll` `AActor::LocalToWorld @ 0x10304ad9` (craft-anything evidence
  `fnd_1`) is the authoritative rotation implementation.

## Session 2026-11-02 (later): full 3-axis actor rotation (`_ue_basis`)

- Root cause of "кривые" tilted actors: `_build_meshes()` applied
  `rotation.y = -yaw` only. Implemented `_ue_basis(pitch, yaw, roll)` in
  `scripts/world.gd` from the UE2 `FRotationMatrix` closed form
  (matches `AActor::LocalToWorld` sin/cos-table math; angles =
  `uint16 · 2π / 65536`, negative stored ints wrap with `& 0xFFFF`):
  rows `X=(CP·CY, CP·SY, SP)`, `Y=(SR·SP·CY−CR·SY, SR·SP·SY+CR·CY, −SR·CP)`,
  `Z=(−CR·SP·CY−SR·SY, −CR·SP·SY+SR·CY, CR·CP)`; Godot Basis columns =
  `C·row` with `C` swapping y/z. Verified in Python: orthonormal det=+1 over
  50 000 random angle triples, and exactly reproduces the old yaw-only
  mapping (max err 0). The naive product `Roll·Pitch·Yaw` is NOT equivalent
  (mismatches ~100% of triples) — do not "simplify" `_ue_basis` back to it.
- `inst.transform.basis` and collision `body.transform.basis` both use it;
  `draw_scale` stays a separate `inst.scale` (basis is unit-scale).
- Re-screenshot (`tmp/shots/live_check/shot1.png`, top-down
  `tmp/shots/dbg/shot1.png`): the previously upside-down `O_DE_MT_obj04`
  (rot `[16336,−117208,0]`, 21 m up) now has mesh-up pointing up. The
  multi-level stone terraces above the spawn road are ORIGINAL geometry
  (`O_DE_MT_obj04` tops ≈ −36 m, `O_DE_Bridge` deck top ≈ −37 m over a
  terrain hole) — earlier "floating slabs" readings were the tilted/flat
  rotations, consistent with DEVLOG 2026-11-01 audit.
- Reference-check shortcut found: the user's DXVK/CACAO install leaves
  **`/Games/ElmoreX3/system/cacaodump_*.pgm`** AO/depth/ssao buffers from
  live original-client frames (see `cacao.log`, `[DUMP]` lines). Current
  dumps are black/flat (RTGI buffers without scene color) — not usable as
  geometry references, but worth remembering.
- Awaiting user visual verification of spawn view before `18_20` migration.

## Session 2026-11-02 (later 2): "two bridges" root cause — hand-edited map.json

- User rejected the spawn view: TWO bridge-like decks stacked, poles floating
  over the character. Full audit of every `StaticMeshActor` against the
  ORIGINAL exports in `tmp/l2/20_18/decrypted/MAPS/20_18.unr` (re-run of
  `python3 -m tools.l2strict extract`, property-by-property diff): exactly
  TWO actors differed from the package — `StaticMeshActor142` (`O_DE_Bridge`)
  Z `-4288.56` → hand-changed to `-4094.6` (+1.94 m), and `StaticMeshActor74`
  (same mesh, east of village) `-4288.56` → `-4257`. These were the
  "bridge_height_fix / bridge_compromise" experiments from the 10-31 session
  that were never reverted; the extra deck + floating poles over the spawn
  road were that second bridge instance, not original geometry.
- Rule going forward: `assets/maps/<map>/map.json` is a BUILD ARTIFACT,
  never hand-edit it; fix data upstream and regenerate with
  `tools/l2strict extract`. Backup of the edited file:
  `tmp/l2/20_18/map.json.edited-backup`; original restored via
  `tmp/l2/20_18/map_fresh.json` (identical to package for all 938 actors).
- `tools/l2strict/verify.py` expected `actors: 804` was stale (pre-Light
  extraction count = 799 SMA + 5 PlayerStart); now 938 (+134 Light). Verify
  passes: status ok, 129 meshes / 211 textures.
- Re-screenshot `tmp/shots/bridge_fix/shot1.png`: single original bridge deck
  at character height with its arches, second slab gone.
- Earlier "floating slabs" note in this DEVLOG (2026-11-01 audit conclusion
  "all three layers exist in the original") was WRONG — the second layer was
  this hand-lifted bridge. Tilted `O_DE_MT_obj04` hillside pieces remain
  original geometry.

## Historical notes (legacy `18_20` pipeline)

The older `tools/l2_*.py` scripts and `assets/meshes`, `assets/textures`,
and `assets/terrain` belong to the first `18_20` attempt. They are kept
for comparison but are not used by the current world. Notable legacy
findings that remain true:

- Import outer chains nest `Object ← Group ← Package`; the owning package
  is the last `Package`-class import in the chain.
- Texture names collide across packages, so textures must be package-scoped.
- UModel refuses glTF animation export from the CLI; use ActorX `.psa`.
- StaticMeshInstance blobs were intentionally skipped; the village renders
  without them.

## Open questions / TODO

- StaticMeshInstance blob format (skipped).
- BSP Brush geometry is not used for rendering (collision only in the
  original client).
- Character material parsing and animation conversion are the next user-
  visible features.
- Steam Audio and export presets are not started.

## 2026-11-06 — CAVE BUGS ROOT-CAUSED AND FIXED: 0fcf0d0 own-importer staging
lost ~20% of the tunnel shell geometry

**User report:** serious bugs in the cave near spawn (X=7309 Y=17720 Z=-4406):
green mossy terrain slopes visible inside the tunnel.

**Diagnosis chain (numeric, no OCR):**
1. Corridor cells hold REAL heightfield data (raw 17176..17481 -> -44 m), not
   the 2511 placeholder — the valley continues under the tunnel down to -71 m.
2. Strict QuadVisibilityBitmap experiment (render present=1 only): the green
   disappeared BUT the floor grid then showed voids east of the road and no
   walkable surface south of the tunnel mouth -> present=0 does NOT mean
   "don't render": the original renders real-height present=0 quads (canyon
   slopes; the 2026-11-03 finding re-confirmed numerically). Reverted
   world.gd to the corner-height rule (git checkout).
3. Floor profile at the user's point BEFORE the mesh restore: top floor was
   MT_Btm (-44.04) with terrain only 0.07-0.5 m below and ABOVE MT_Btm at the
   west end (-44.25 vs -44.55) -> z-fighting/poking green.
4. **Root cause:** stage commit 0fcf0d0 re-staged 26 meshes with our own v3
   importer. O_DE_MT_Out .bin shrank 207872->162422 B (-22%), MT_In -19%,
   MT_Btm -19%, and O_DE_inlet LOST ITS FLOOR SECTION ENTIRELY (no inlet hits
   in the profile at all). The inlet is a huge single mesh = the whole gated
   passage (walls + ceiling + floor). Without its floor, the corridor terrain
   (grass-masked canyon) showed through = the green cave bug. Same class of
   gap for every re-staged mesh (known blockers: L2 variable header unk1/
   unk2/unk3/unk4 offset shifts; 32-B class sections after the index streams).

**Fix:** restored all 26 mesh .gltf/.bin pairs to the UModel exports
(`git checkout 0fcf0d0^ -- <files>`), deleted their .import stamps and
.godot/imported, re-imported headless. UModel exporter geometry is exact
(bfd887c). The own importer remains the future path — it must first solve
the L2 variable header and the 32-B class before replacing UModel staging.

**Verification (after fix):**
- E-W profile through (7309,17720): top surface at every point is a MESH —
  inlet floor -44.18..-44.22 (west) / MT_Btm -44.04..-44.49 — terrain always
  below; O_DE_inlet spans the whole tunnel (rock bands -33.6/-36.2 + floor).
- N-S profile at x=7100 (across the mouth): 0 points without a walkable
  surface (-46..-30 band), 0 terrain hits above -44.0 (no pokes).
- Screenshots at the user's point and at spawn: ornamental road + dark
  pillars + rock walls + statue in fog; NO green terrain inside the cave
  (tmp/shots/shot1.png, tmp/shots_spawn/shot1.png).

**Parked:** EdgeTurnBitmap as the triangulation diagonal (loader was wired
then reverted with world.gd; the corner rule already renders correctly).
The strict-present experiment is documented here only — do not repeat it as
a render mask.

## 2026-11-06 (later) — residual "grass from the outer texture" inside caves:
CULL_DISABLED backface leak, replaced with per-face winding flip

**User report:** small grass-textured pieces remain inside caves at
(7096,17888) and (6141,18673) — "the old bug we already fixed".

**Diagnosis (numeric):**
- Floor grid at the chamber (5950-6550, 18350-18950): 625 points, terrain
  hits = ZERO. The green wall is NOT terrain — it is a mesh face.
- The wall's texture = DE_V_m06 (oren_dev_t) — a mossy grass-over-rock
  texture legitimately assigned to O_DE_MT_obj01 section 1 by materials.json
  (primitive_material_indices [0,1,2,3], verified against the glTF).
- The face is the BACKSIDE of an exterior mossy surface, visible because
  `_down_floor_meshes` disabled backface culling on whole meshes (the UE2
  two-sided emulation added for down-normal floors). obj01/MT_In/MT_Out/
  inlet were in that list; obj02-04 and MT_Btm (not in the list) never leak.
- Winding analysis: glTF winding agrees with stored normals on EVERY face
  of obj01 (0 down-normal faces at all) and inlet (368 down-normal floor
  faces, duplicates MT_Btm whose faces are all up-normal).

**Fix (world.gd _get_mesh):** replaced the whole-mesh CULL_DISABLED hack
with a per-face winding flip for meshes in `_down_floor_meshes`: faces whose
vertex normal points down (y < -0.5) get their index triple reversed, so the
floor becomes front-facing from above; every other backface culs normally.
This reproduces UE2's two-sided-from-above result without exposing the
backsides of exterior surfaces. Collision untouched (backface_collision
stays on the trimesh; winding is irrelevant to ConcavePolygonShape3D).

**Verification:**
- Chamber (6141,18673): green wall gone — dark rock + the inlet floor
  (now front-facing) render instead.
- Mouth (7096,17888): the mossy patch gone.
- Bridge (8000,17650): deck still renders (the flip preserves the down-face
  visibility that CULL_DISABLED provided) — the original motivation for the
  hack holds.
- Spawn (7400,17650): unchanged composition, no green in the cave volume.
- E-W profile through the tunnel: 21/21 points with deck floor; N-S across
  the mouth: 26/26 points walkable. No collision regressions.

**Parked (mask-orientation investigation):** slope-correlation test of the
terrain masks suggests the alpha maps may be DIRECT-mapped (no V-flip):
ST rock correlates with steep quads ×25 under DIRECT vs ~0 under the current
V-flip, road-bed cells are dirt-only under DIRECT. Not applied — the open-
terrain look was user-approved with the current flip and the cave-green bug
turned out to be mesh backfaces, not masks. Revisit with original-client
reference screenshots before touching the shader.

## 2026-11-07 — importer v6: UModel-exact axes, real UVs, plan-fallback
sections; 27 meshes staged from our own code

**Three defects found and fixed in tools/l2strict/staticmesh.py:**

1. **Y-axis mirror.** Our glTF mapping was (gx, gz, -gy) — a PROPER rotation
   — while UModel's (the in-game verified reference) is (gx, gz, +gy): an
   improper transform with the raw face order kept. Byte evidence: Pir01
   file vert0 (92.38, 45.64, -529.78) = UModel (0.924, -5.298, 0.456) x100
   = (x, z, y) — the DEVLOG final6 note read literally; plus the fence01
   bbox: the file bbox (arbiter) has game-Y as the long axis, UModel's
   glTF carries it in glTF-Z un-negated. Winding check: 40/40 faces match
   UModel's order with NO swap (UE's raw winding is opposite-handed, so
   the mirror lands on glTF CCW correctly). Fix: positions (x, z, y)*0.01,
   normals (nx, nz, ny).
2. **Zero UVs (the "flat untextured" regression).** The color/alpha/UV
   stream walk `continue`d to the NEXT width on a count mismatch — the
   Bridge's UV stream carries a stray 0x01 byte before its compact count,
   so the width-8 attempt failed and every staged mesh rendered with
   (0,0) UVs (solid texture-corner color). Fix: retry the SAME width over
   a 16-byte window. Also: stride-32 anchors now read their inline UVs;
   and a latent `mesh["uvs"][0]` unpack bug (uvs is a flat tuple list)
   surfaced and fixed.
3. **Hint multiplication.** The vertex hint summed POSITION counts over
   primitives; our own exports share one pool accessor across all prims,
   so re-running the converter on our own staging multiplied the hint by
   the prim count (9468 = 9x1052) and poisoned the anchor. Fix: sum
   UNIQUE accessor indices.

**Section plan fallback (the 32-B class):** when the on-file 14-B section
table resists the oracle (it serializes behind the L2 variable header and
the kDOP object — the engine.dll order is bbox/sphere -> L2 header ->
5x FStaticMeshVertexStream -> 2x FRawColorStream -> 1 stream -> 2x
FRawIndexBuffer -> kDOP UObject -> sections (+0x148) -> +0x160 array),
the staged UModel glTF's per-primitive index counts (they sum EXACTLY to
the real render-pool length) slice the file's real index pool contiguously
and carry the per-section material indices (Pir01: [0,1,2,3,4,6,7,8] —
material 5 unused). The index VALUES stay from the file — UModel's own
indices for this class are fabricated (sequential runs).

**Result: 27 Oren_DEV_S meshes staged from our importer** (git history
keeps the UModel versions). Validation vs UModel: bbox 27/27 exact,
UVs non-zero everywhere, prim counts and material mappings 1:1 — with
REAL file indices where UModel fabricates them. Skips remain: inlet,
Btm_Obj01, MT_obj01-03 (packed-vertex anchor RE pending), Btm_Obj02/03 +
DE_effect + Etc_Bridge02 (not staged at all).

**In-engine verification:** bridge deck 26/26, tunnel deck 21/21 profile
points; spawn and Pir01 pillar screenshots textured correctly (the pillar
shows its ornamental deco band — the material mapping works).

## 2026-11-07 (2) — the bridge resolved: the two levels are authentic

**The user's standing bridge complaint ("пол в 2 уровня", "провалился в
нижний ярус, второй слой сквозной") — root-caused and closed:**

- Fine cross/axis floor profiles at the bridge (7987-8700, 17624): EVERY
  point carries BOTH the ornamental road deck (O_DE_Bridge, -45.3..-46.8,
  the sunken walkway with the filigree strips) AND the side curbs
  (O_DE_Btm_Obj01, -44.0..-44.7, 0.8 m above). The "two levels" are the
  authentic Dark Elf bridge shape: a sunken ornamental road between raised
  curbs. The Btm_Obj01 mesh is a REAL 34x2.6x2 m box (24 verts, 2 instances
  = the two sides) — its bbox matches the file bbox exactly, so UModel's
  decode of it was correct all along.
- The "fell through into the lower tier" defect = the deck's down-normal
  faces without backface collision — fixed earlier (backface_collision on
  all trimesh colliders). Re-verified today: the cross-profile is 21/21
  walkable (-46.6..-42.5 band), the deck present at 21/21, the curbs at
  21/21. No through-gap remains.

**Importer hardening (tools/l2strict/staticmesh.py):**
1. bbox invariant: the parsed vertices must fill the file's own bbox
   (tolerance max(8 cm, 5% of span)) — a mismatch now raises instead of
   silently staging a false-stream mesh. This is the check that exposed
   the Btm_Obj01 story.
2. bbox-plate fallback for the packed-vertex class: when a mesh has no
   f32 records and its bbox is a thin plate (z-span < 2 m), reconstruct
   the plate box from the exact bbox corners (raw-frame verts, outward-CCW
   glTF windings, planar 2.56 m UVs, the first material). Applied to
   DE_effect (a thin plane) in the scratch run; NOT staged — effects are
   not road-critical and a box approximates an effect plane poorly.
   Btm_Obj01/02/03 do NOT take this path (their bboxes are thin in Y, not
   Z, and their UModel boxes are already correct).

Still parked: the truly packed-vertex meshes (inlet, Btm_Obj01's SIBLINGS
Btm_Obj02/03 are unstaged but their UModel boxes decode fine when staged;
MT_obj01-04, H03/H04, MT_Out, SH, CH_Btm/stairs, Center_obj — the anchor
finds no f32 stream) — the packed u32-vertex format from
FStaticMeshVertexStream<< (engine.dll 0x1030bdcf: the stream = a u32
array) is the next RE target.

## 2026-11-07 (3) — BREAKTHROUGH: the sections serialize BEFORE the bbox

**UEViewer's UnMesh2.cpp UStaticMesh::Serialize (the reference decode that
works for L2):**
```
Super::Serialize(Ar);          // UPrimitive = the properties
Ar << Sections;                // <-- THE SECTIONS, right after the props
Ar << BoundingBox;             // "UPrimitive field, serialized twice"
Ar << VertexStream << ColorStream << AlphaStream << UVStream
    << IndexStream1 << IndexStream2 << f108;
goto skip_remaining;           // the kDOP/collision is never read
```
Our parser reads `bulk = props_end` and treats bulk+0 as the bbox — for the
L2 layout the SECTIONS sit between the props end and the bbox, i.e. in the
region our parse never scans for tables (the L2 20-B "units at +41" were
the L2 header — final7 — and the real section tables are PRE-bulk).

**Pre-bulk dumps (recorded for the next pass):**
- O_DE_Btm_Obj01 (bulk=7176321, props end 176): the region bulk-160..-16
  = a repeating ~12-14 B pattern `04 53 00 01 53 00 02 d3 00 03 15 c0 01 00`
  with one varying byte per unit; before it: `ff..ff 04 00 00 00 00 00 00
  00 08 00 00 00 00 00 00 00 05 59 ac 0d` — an i32 8 (a count?) near -186.
- O_DE_Pir01 (bulk=5848552, props end 122): `ff ff ff ff ff 0d 00 00 00
  00 00 00 00 08 00 00 00 00 00 00 00 05 59 76 09` then the same repeating
  pattern `04 53 00 01 53 00 02 d3 00 03 05 XX` (XX varies: 84 94 8f 85 9e
  8b 9f 90 97 88 ae) — an i32 8 (the section count? Pir01 has 8 sections)
  near -131, and i32 13 (`0d`) near -139.

**FStaticMeshSection = the SAME 14-B layout for every class** (UEViewer
asserts Ver>=112): f4(i32), FirstIndex, FirstVertex, LastVertex, fE,
NumFaces (u16 x5). FStaticMeshVertexStream = [TArray<FStaticMeshVertex>]
[Revision i32]; the vertex = Pos+Normal (6x f32) for the standard class.

**The bridge/house height story (the user's ground truth: the bridge road
= ONE wide layer = the house floor level):** the road-adjacent meshes
(Btm_Obj01 curbs, H01-04 house floors) belong to the packed-vertex class —
their CURRENT geometry (UModel/ours) carries wrong positions, which is why
the curbs poke 0.8 m above the deck and the H03 floor reads -41.95. The
packed u32-vertex format (FStaticMeshVertexStream<< = engine.dll
0x1030bdcf = a u32 array via ByteOrderSerialize) + the pre-bulk section
tables = the next session's RE targets; both are now precisely located.

## 2026-11-07 (4) — the temple joins the packed family; RE state snapshot

**The user's report:** the Shilen Temple (sylen_temple_s package, the east
structure at x~26030) is missing floors and stairs (sylentemple_ent_stair,
ent_stair02, side_stair) — the same packed-vertex class as the bridge curbs
(Btm_Obj01-03) and the house floors (H01-04). The sylen_temple_s package has
never been processed by our importer at all; its staged meshes = UModel.

**The packed class (known members so far):** Btm_Obj01/02/03, DE_effect,
MT_obj01-04, H03/H04, MT_Out, SH, CH_Btm, CH_sidestair, CH_mainstair,
Center_obj, inlet, the sylen temple stairs/floors. All the visible
"missing floors / wrong heights" defects map to it.

**engine.dll structure (verified across sources):**
- UPrimitive::Serialize (the L2 parent) = the props + THE SECTIONS TArray
  (sub_1030a41b, count at +0x34, data at +0x60 — serialized right after the
  props, BEFORE the bbox) — matches UEViewer (Ar << Sections; Ar <<
  BoundingBox; ...).
- UStaticMesh::Serialize (Ver>=0x70): 5x FStaticMeshVertexStream,
  2x FRawColorStream, 1 more stream (sub_10303ff8), 2x FRawIndexBuffer,
  kDOP UObject (sub_10308788), the lazy arrays +0x148/+0x160 (sections?),
  then Ver<0x72 / Lic>=6,7,11,13,14,15 small reads; InternalVersion=8
  (i32, Ver>=0x51); +0x1f0 (Ver>=0x64); +0x1e0 (Ver>=0x78).
- FStaticMeshVertexStream<< (0x1030bdcf) = [count via sub_10305f29(stream+12)]
  [ByteOrderSerialize(data, 4)] — the stream payload = 4-BYTE elements = the
  packed vertices. sub_10305f29 = the array reader — NOT yet studied.
- The L2 ULodMesh branch (UEViewer): ArVer >= 133 stores the vertices as a
  PLAIN FVector array (12 B each, f32) — our packages are Ver 123, so the
  packed format applies; ArVer>=133 = a later simplification.

**Pre-bulk region facts (the sections live here, before the bbox):**
- Btm_Obj01: repeating 14-B-ish units `04 53 00 01 53 00 02 d3 00 03 15 c0
  01 00` (one varying byte c0/c1/... per unit) after `ff..ff | 04 00 00 00
  | 00 00 00 00 | 08 00 00 00 | 00 00 00 00 | 05 59 ac 0d`; wider region
  has float blocks with 0.99-normals between FF-runs.
- Pir01: `ff ff ff ff ff | 0d 00 00 00 | 00 00 00 00 | 08 00 00 00 | 00 00
  00 00 | 05 59 76 09` then the same repeating units (the varying byte:
  84 94 8f 85 9e 8b 9f 90 97 88 ae).
- The Bridge-style 14-B section tables (f4=0 + ascending FirstIndex) are
  NOT found pre-bulk — the packed class uses a different section/vertex
  encoding; the engine's element serializer (the vtable call inside
  sub_1030a41b) is the ground truth to mine next.

**Next session plan (fresh context, pick up here):**
1. native_function_study sub_10305f29 (the stream array reader) and the
   element operator it dispatches to — that yields the packed vertex struct
   (probably i16 XYZ + the bbox scale/base, cf. UEViewer's UC2 decoder:
   Pos = i16/32767/Scale + Base).
2. Mine the L2 UPrimitive::Serialize (engine.dll) around sub_1030a41b for
   the section element layout of the packed class.
3. Decode Btm_Obj01 end-to-end (validate: the verts fill the file bbox
   34x2.6x2 m; the road plate = ONE wide layer at the PlayerStart height
   -44.79 per the user's ground truth).
4. Apply to sylen_temple_s (the stairs ent_stair/ent_stair02/side_stair +
   the floors) — the package needs its own convert pass.

## 2026-11-07 (5) — THE PACKED-VERTEX MYTH DEMOLISHED: run-anchor decodes everything

**The phantom "packed-vertex class" never existed.** The real cause of every
"undecodable" mesh: the vertex stream sits at an offset NOT aligned to the
bulk start, and the old scans were either aligned to 24 bytes (missing the
stream entirely) or hinted by UModel's wrong counts. Evidence:
- sub_10305f29 (engine.dll) = the TArray serializer with 0x18 = 24-byte
  elements = FStaticMeshVertex (Pos+Normal, 6x f32) for ALL static meshes.
- Btm_Obj01: an unaligned scan finds a count-guarded 20-record run at
  bulk+426 (the first vert = the bbox max corner exactly); UModel said 24.
- inlet: a 1384-record run at bulk+236 — a plain 24-B stream.

**The new anchor (staticmesh.py):** scan the serial region with numpy over
all 24 byte phases (the record stride = 24 B), collect the maximal valid
runs (>= 8 records), pick the run whose preceding compact count equals its
own length (the count-guard rejects the kDOP float blocks). No staged-glTF
hints anywhere. The vertex data must fill the file bbox (the invariant).

**The section scan widened** to the pre-bulk region (max(0, start-4096)) —
the L2 tables serialize before the bbox (the 2026-11-07 (3) finding).

**Result: 43/43 Oren_DEV_S + 26/26 sylen_temple_s meshes converted from our
importer and staged** (69 files; Btm_Obj02/03 + DE_effect gained asset_map
entries). The section tables decode 1:1 with UModel (H03 17 prims, MT_obj01
4, MT_Out 5, the skin 20/20). The temple floors (sylentemple_skin at -24.1
..-24.8 through the great hall) and the stairs (ent_stair 168 verts/3
sections, ent_stair02 252/3, side_stair 96/2) are now real geometry.

**Bridge after the fix:** the road bed (Btm_Obj01, pitched -12.48 deg =
the road slope to the village) is a SMOOTH ramp -44.38 -> -46.11 along the
axis (the old jittery slab faces gone); the player stands on it at -44.9;
the road = the ornamental center strip + the stone deck = one surface. The
0.68 m ledge at x~8555 where the plate butts the Bridge deck remains and is
the exact-mesh data.

**H03 floor = -41.95 from the REAL geometry now** (the invariant-passed
mesh) — the houses stand on terraces above the road; verify in game.

## 2026-11-07 (6) — trace-box tool; the temple state after the run-anchor staging

**New instrument: L2_TRACE_BOX="x1,y1,x2,y2"** (world.gd) — casts rays from
the camera through every 8th pixel of a screen rect and reports the hit
mesh, face, surface and the resolved texture + totals. The permanent
answer to "what is this surface" for ANY suspect region.

**The temple at the user's spot (26030,11038) after the v7 staging:**
- TRACE totals: ent_main 747, pir 294, deco11 110, ent_stair 36,
  ent_stair02 22, deco12 36, the statue, deco01/04 — THE STAIRS RENDER
  (the real geometry from our importer), all hits carry resolved textures.
- The flat brown mid-hall area = the ent_main surface (surf 1, texture
  oren_sylen_in020 — a DARK stone texture) lit by the warm NSun: the
  brown = the sunlit dark stone, not a missing texture (all 26 temple
  meshes resolve every material file; zero zero-UV meshes).
- The floors: the sylentemple_skin floor at -24.1..-24.8 spans the whole
  hall (the profile, no gaps).
- The user still reports "no changes" — the visible difference vs the
  original remains unidentified; the candidates: (a) the sun should be
  blocked by the roof (the shadow map question — the lighting stage),
  (b) the section->material binding differs from the identity in the L2
  engine, (c) the UV convention per the engine.

**The engine dive queue (the user's directive: "разбирай ещё больше
движок"):** the L2 UPrimitive::Serialize section element layout (the
vtable call inside sub_1030a41b), the section->material binding in the L2
renderer (is it Materials[i] or the section field?), the L2 UV
conventions for the static mesh streams, the NSun/shadow interplay for
the interiors. Each = native_function_study targets in engine.dll.

## 2026-11-07 (7) — the user reports 0 visible changes; the honest state

**The user ran the build after the v7 staging: the temple and the bridges
look unchanged.** The numeric state DID change (the bridge ramp is smooth,
the profiles differ), but the visible composition is the same: the bridge
still reads as the strip + the deck, the temple hall still has the flat
brown mid-ground. The user's ground truth stands: the original bridge =
ONE wide layer, the house floors at the same height.

**The header-float test (this session):** the L2 header unk1/unk2/unk3/unk4
regions in the bulk are zeros/NaNs for Pir01, Btm_Obj01 and Bridge — there
is NO vertex offset/scale hidden in the header. The vertices are absolute.

**New structural facts:**
- The Bridge (the 24-B class) keeps its 18 section units AT bulk+24
  (18 x 14 B = 252 B, then the vertex stream at +321) — in-bulk.
- The Pir01 pre-bulk table (8 x ~12 B after the i32 counts 13/8) does NOT
  contain the face-count values the UModel prims imply (76/43/12/4/8/16/8/12
  are absent) — so it is NOT the section table; likely the vertex/wedge
  remap (the "dual counter" units from the 2026-11-06 final5 note).
- Pir01 carries TWO bbox copies (bulk+0 and bulk+168 — UPrimitive's
  BoundingBox "serialized twice" per UEViewer).

**What this means for the bridge:** the geometry of every piece is now
byte-validated against the file bboxes, yet the composition (the 2.56 m
plate over the wide deck) contradicts the user's one-layer ground truth.
The remaining unknowns are RENDER-side, not parse-side:
  1. the section->material binding in the L2 engine (UEViewer assumes
     Materials[i]; the engine may index differently — the flat brown
     surfaces are the prime suspect),
  2. the draw transform: whether the L2 client adds a per-mesh offset
     (the mesh origin vs the bbox) on top of the actor Location,
  3. the possibility that some road meshes are simply not yet identified
     as present (the actor->mesh role mapping for Btm_Obj01/02/03).

**Next session: mine the RENDER side of engine.dll** — the static mesh
draw path (the section/material/vertex-stream binding at draw time), and
AActor::LocalToWorld usage for the static mesh components. That decides
the visible composition question once and for all. The trace tools
(L2_TRACE_BOX / L2_GREEN_TRACE) are in place to verify each hypothesis
against the rendered frame.

## 2026-11-07 (8) — the bbox invariant was CIRCULAR; the packed-class parses are garbage

**The user's "0 changes" was correct and the reason is found:** for the
meshes whose section tables serialize pre-bulk (Btm_Obj01/02/03, the
temple stairs family?), the value I read at bulk+0 as "the bounding box"
is NOT the bounding box (the sections live there). The run-anchor then
found "vertex streams" inside that garbage, and the invariant validated
the vertices against the SAME garbage bbox — a circular check. The staged
Btm_Obj01 "plate" (a 2 m thick box) is misread table bytes; the real road
plate is a thin plate at the road level.

**The road level is established exactly:** the UE PlayerStart's Z is the
PAWN ORIGIN (the capsule center), not the floor. PlayerStart = -4478.9 =>
the capsule center -44.79 => the floor ≈ -44.79 - ~0.85 ≈ -45.6. The
Bridge deck = -45.4..-45.6 = THE ROAD. Our deck was correct all along;
the garbage "plates" stick ~1.5 m above it and read as the "second level"
the user sees on the bridge.

**Consequences:**
- Every mesh whose sections serialize pre-bulk must be re-parsed after
  the true bbox location is established. The candidates = the whole
  pre-bulk family (Btm_Obj01/02/03, DE_effect, the temple stairs?).
- The bridge composition question is settled numerically: the road =
  the deck (-45.4..-45.6); the curbs/parapets sit above it; the garbage
  boxes must become thin flush plates.

**Next session (single focus):**
1. Establish the true bbox/sections order per class: dump Bridge
   (in-bulk sections at +24 = the working reference) vs Btm_Obj01
   (pre-bulk tables) — find the real bbox offset for the pre-bulk class
   (the engine reads it AFTER the sections: UPrimitive::Serialize emits
   the sections, THEN the bbox — so for the pre-bulk-class meshes the
   bbox = AFTER the pre-bulk tables, NOT at bulk+0!).
2. Re-parse the pre-bulk family with the corrected offsets; validate
   the plates: thin (<0.3 m), top at the road level (-45.6 on the
   bridge).
3. Stage; the bridge becomes ONE wide flush layer per the user's ground
   truth. The reference: ask the user for a fresh DE_village.png from
   the bridge spot (the current file = the Oct 29 spawn view).

## 2026-11-07 (9) — THE BRIDGE SOLVED (the composition): the curb plates are raised garbage

**The user's revelation:** DE_village.png IS the bridge — the spawn view
looks east along it. In the original it is a WIDE ROAD with the golden
ornamental border strips at the edges, flat. In our build it became a
"raised walkway over the abyss": we only have the middle strip, and the
player walks ON it (the HUD Z = the strip top -44.06).

**The composition decoded:**
- Btm_Obj01/02/03 = the ORNAMENTAL BORDER STRIPS of the road (2.56 m wide,
  2 instances = the two edges; 34 m long). In the original they are flat
  curbs flush with the road surface.
- Ours are 2-m-thick boxes sticking ~1.5 m above the road => the player
  climbs onto the strip => "the hanging walkway", "only the middle".
- The road itself = the Bridge deck (-45.4..-45.6 = exactly the
  PlayerStart Z minus the pawn half-height) — correct all along.

**The root cause (final):** for the pre-bulk-table meshes the value at
bulk+0 is not the bbox, so the run-anchor's "vertices" are table bytes and
the circular bbox invariant passes them. The real thin plates are still
undecoded. Everything else (the deck, the tunnel floors, the temple shell)
is real geometry.

**The fix (next session, single focus):**
1. Locate the true bbox for the pre-bulk class: the engine order is
   props -> sections -> bbox, so the bbox sits AFTER the pre-bulk tables —
   scan for the second float sextet (Pir01 has it at bulk+168! — find the
   same pattern in Btm_Obj01/02/03).
2. Re-run the vertex stream search AFTER the true bbox; validate: the
   plate = thin (z-span < 0.3 m), its top = the road level.
3. Re-stage Btm_Obj01/02/03: the bridge becomes the flush wide road with
   the flat border strips per DE_village.png.

## 2026-11-07 (10) — THE PLATE DATA LOCATED: variable-length packed vertices

**The road plate's real vertex data found in Btm_Obj01's bulk** at
rel+2779..+4233: flat-plate vertices with z = -102.87 CONSTANT (the plate
is FLAT, 22 m x 2.56 m: x in [-553..1651], y in [-128..128]) — at the world
height -46.11 = the deck level = THE ROAD. The z=-102.87 sextets repeat
through the region (the scan's "thin bbox" hits are the plate's own
vertex pairs).

**The vertex entry format (visible in the raw dump):** variable-length
units `[01][index: 01,02,03,...,0c,0d][length: 09,0a,0b,0c,0d][data...]`
— the length byte VARIES (9..13 B) = delta/packed encoding, NOT a fixed
stride. This is why every fixed-stride scan (24/32/36 B) failed on this
class and why the "runs" found earlier were garbage.

**Consequences:**
- The plate's true geometry = a flat 22x2.56 m slab at the road level —
  the decode requires the packed-entry format (the next session's single
  focus: mine the L2 decompressor in engine.dll — the stream reader that
  walks these length-prefixed entries; sub_10305f29's 24-byte path is the
  UNPACKED variant, the packed class uses a different element reader).
- The bridge = ONE wide layer away: the deck (-45.4..-45.6 = the road) is
  correct; the border strips (Btm_Obj01/02/03) decode flat and flush =>
  the bridge matches DE_village.png.
- The temple floors/stairs and the other "packed family" members share
  this format (the same variable-length entries) — one decoder fixes all.

## 2026-11-07 (11) — THE BRIDGE IS ONE LAYER: flat plates extracted and staged

**The road-plate extractor implemented** (staticmesh.py `_flat_plate_mesh`
+ the `_ROAD_PLATE_MESHES` family): scans the bulk for vertex triplets
sharing a constant height (the L2 file vertex = (X, Z, Y) — the height is
the SECOND column; Btm_Obj01's plate collapses to z = -102.87 while the
column-0 spans 22 m and the column-2 spans 2.56 m), builds the thin
12-cm slab from the cluster bounds with the planar 2.56 m UVs and the
first material.

**All three strips extracted and staged** (Btm_Obj01/02/03): 8 verts each,
the glTF height range -0.12..0.00 relative to the actor = the plate top at
the actor Z = -45.08 = **flush with the road** (a 40-cm curb at most).

**The bridge profile after the fix (7900..8700 along y=17630):** the top
walkable surface = DECK at EVERY point (-45.14 -> -46.79, the smooth
descent) — NO strip/deck transitions, NO second level. The bridge = ONE
wide layer per the user's ground truth (DE_village.png).

**Remaining:** the same flat-plate treatment for the rest of the
variable-length family when their roles demand it (the temple floors/
stairs keep their real 24-B geometry where the count-guarded runs are
genuine); the packed-entry decompressor for the full fidelity (the exact
strip outlines instead of the bounding slabs).

## 2026-11-07 (12) — the plate experiment reverted; the road = the strips at -44.06

**The user's verdict on the flat-plate experiment:** "теперь просто нету
верхнего слоя, только нижний. это не фикс" — sinking the strips under the
deck removed the walkable upper layer. Combined with the earlier reports
the picture is now complete and consistent:

- THE ROAD = the strip layer at **-44.06** (the user's walking HUD height,
  = the plate tops). In the original the strips form the FULL-WIDTH road
  surface at that height ("один широкий слой").
- Our strips are only 2.56 m wide ("у нас от неё только середина") because
  the packed delta-encoded entries are undecoded: the flat-z scan caught
  only the base subset (y ±128) of the full-width plate.
- The Bridge deck (-45.4..-46.8) = the structure BELOW the road, visible
  at the openwork sides — correct as geometry.

**The single remaining task for the bridge:** decode the packed
delta-encoded vertex entries (the [01][idx][len 09..0d][data] units in
Btm_Obj01/02/03's bulks, rel+2779..+4233 in Obj01) — the full-width plates
at z = -102.87 (world -44.06 at the -4508 actor) replace the narrow ones.
The v7 boxes are re-staged until then (the wrong width but the right
height and walkability).

**The decoder clues accumulated:** the entries are length-prefixed
(09..0d bytes), sequential per vertex (the counters 01,02,03...), the
constants inside = -103.49 (the z), 1651.04 / -553 (the x bounds), ±128
(the y bounds); the 12-B separators between the entries = the counters +
the type bytes (09/0a/0b/0c/0d = the lengths). The mineable code path =
the L2 static mesh loader in engine.dll that walks these entries (around
the FStaticMeshVertexStream handling, sub_10305f29 is the UNPACKED
variant).

## 2026-11-07 (13) — the vertices were always fine; the PACKED ENTRIES ARE THE FACES

**Reframing after the user's "make the wide bridge, continue the decoder":**
- The 20-record pool at Btm_Obj01 bulk+426 = the REAL plate vertices —
  vert0 = (1651.04, -64, -102.87), ALL z = -102.87 (the flat plate at the
  world -46.11 with the -4508 actor). The vertices were never the problem.
- The variable-length entries at bulk+2779..+4233 (`[01][idx 01,02,03...]
  [len 09..0d][data]`, the 29-byte visible period) = THE TRIANGLES/FACES
  in the L2 compressed format — NOT vertices. Our pipeline takes the faces
  from the UModel prim plans (fabricated) => the box instead of the plate.
- So the fix = decode the packed FACE entries: each entry presumably packs
  the triangle's wedge/vertex references (+ the edge flags) in len bytes.
  The 29-byte period = the entry + the following vertex coords repeated
  in the clear (the float runs -128.0/-103.49/1651.04/128.0/-103.49 =
  the (Y,Z,X)-ordered plate corner coordinates visible between entries).

**The engine hook:** these entries are the LAZY arrays (+0x148/+0x160 in
UStaticMesh, sub_1030ac90/sub_10308c6a — serialized AFTER the streams,
skipped by UEViewer's `goto skip_remaining`). The L2 loader walks them
with the length-prefixed records — mine sub_10308c6a and the element
serializer it dispatches.

**Interim state:** the v7 boxes are staged (the right height, the wrong
faces). The plate decode = the next session's single focus:
1. native_function_study sub_10308c6a + the element op (the triangle
   decompressor).
2. Decode Btm_Obj01's entries -> the faces; validate: sum(tris) covers
   the 20-vert plate flat in z.
3. Same for Btm_Obj02/03, then re-stage: the bridge = the flat strips at
   -44.06 = the full road per DE_village.png.

## 2026-11-07 (14) — the lazy array structure decoded (sub_10308c6a)

**sub_10308c6a (the +0x160 lazy array serializer):**
- the count via sub_1030599d (the compact/int reader),
- the in-memory elements = **44 bytes each (imul 0x2C)**,
- the element serialization dispatches through vtable+0x3c (the element
  op) — the ground truth for the record format.

**The file-side units in Btm_Obj01's packed region (~29 B each):**
- the 5-B header: `01 | XX | YY | 81 | 81` where XX = the sub-index
  (00,01,02,03,...,10,11 — walks the segments) and YY = the growing
  length byte (06,08,09,0a,0b,0c,0d,0e,0f,10,11),
- the 24-B data = six unaligned f32s. Sample (the unit at bulk+2716):
  `01 10 06 81 81 | (-882.1, 64.0, 103.5 | -1341.6, 128.0, 103.5)` —
  plausible plate coordinates (x within [-1762..1651], y within
  [-128..128], z within [-103..103]), two 3-float groups per unit.
- the clear float runs between the headers = the plate's cross-section
  constants: y = ±128, z = -103.49/-102.87, x = 1651.04 / -553.

**The picture:** the L2 lazy array = the per-segment records of the
extruded road strip; the 44-B in-memory element = the unpacked record
(the segment's vertices + the link fields); the file record = the 29-B
packed unit with the growing payload. The decompressor = the element op
behind vtable+0x3c in sub_1030ac90's loading path (or the twin dispatch
inside sub_10308c6a at 0x106f6ca6/0x106f6cb3) — the exact functions to
mine next session. One decoder unpacks the strips => the bridge = the
full-width road; the same format family covers the house floors and the
temple pieces.

## 2026-11-07 (15) — the units are SECTION RECTANGLES; the box is real

**The 29-B units decoded as vertex pairs** (the scan `[01][XX][YY][81 81]`
+ 24 B = 2 vertices): 17 units, the pairs = the DIAGONAL CORNERS of
rectangles:
- the z = -102.87 family: (-553.26, -128) -- (1651.04, 128), (-1304.83,
  -128) -- (-553.26, 128), etc — the plate's bottom rectangles,
- the z = +103.48 family: (-1762.47, -128) -- (-1304.83, 128), etc — the
  top rectangles.
The XX = the section index (0..17), the pairs = each section's bounding
rectangle. **The Btm_Obj01 mesh IS a real 34x2.56x2 m box** (the
vertices were byte-validated; both UModel and our run-anchor agree).

**The placement insight:** the actor (9059, 17388) + the box y-span
[-128..128] = the world y 17260..17516 — the road line is y ~17630 =>
**the box = the road's NORTH CURB**, not the road itself. The second
instance (13698, 16320) = the next segment's curb. The road surface
between the curbs = the Bridge deck (-45.4..-45.6 = the correct level).

**The open question (needs the live-client reference):** the original's
bridge shows the golden border strips AT the road edges, flat. If the
Btm_Obj01 box is the north curb, its top (-44.05) rides 1.35 m above the
deck — in the original the curb top is presumably much lower (a flat
border) or the visual reads differently. A fresh DE_village.png capture
standing ON the bridge (x~8000-8500, y~17630, looking east) settles:
(a) the curb height, (b) whether the golden strips are the same
Btm_Obj01 boxes with a different Z, or separate deco meshes.

**The tooling ready:** the unit scanner (this session's script,
tmp/-disposable), the L2_TRACE_BOX tracer, the floor profiles. The
staged state = the v7 boxes (the real geometry, the right height).

## 2026-11-07 (16) — THE BRIDGE REFERENCES SAVED; the composition finally clear

**Four live-client captures saved to Docs/** (bridge_original_spawn/level/
side/tunnel.png). The analysis:

1. The road = ONE flat wide cobblestone surface (the Bridge deck — our
   deck is correct and present).
2. The ornamental filigree patterns (the spider-web designs) = FLAT
   INLAYS ON the road surface — thin decorative slabs laid on the road,
   NOT raised strips. They run transversally across the road and along
   the edges.
3. No curbs/walls along the road; the low railings sit outside the road
   surface.

**Consequently: Btm_Obj01/02/03 = the FILIGREE INLAY SLABS** — thin
plates lying on the road with the ornamental texture. Our 2-m-thick box
= a misdecode (the real thin slab decodes from the packed entries; the
flat-plate scan already found the clear vertices at z = -102.87).

**The height question for the next session:** the extracted plate reads
world -46.11 (with the -4508 actor) while the road surface at the bridge
spans -44.4..-46.8 (sloping). Either (a) the plate = the under-slab and
the visible inlays = OTHER instances/meshes, or (b) the actor Z of the
strip instances must be re-checked against the map (the instances at
9059/13698 cover different road segments). The trace tool against the
live-client captures will pin the exact placement.

**The remaining work (unchanged):** the packed-entry decoder (the
variable-length [01][idx][len][data] records) => the real thin inlay
slabs => laid on the road => the bridge matches the references.

## 2026-11-07 (17) — the flush road plates implemented and staged

**The flat-plate extractor hardened** (staticmesh.py):
- the finite-triplet filter (the NaN garbage floats excluded),
- the circular bbox invariant scoped to the standard parse path only
  (for the road-plate family the value at bulk+0 is not the bbox),
- the flat-strip faces = the quad chain between the consecutive
  cross-section pairs, the winding normalized per quad by the normal z
  (the plate's top up).

**All three strips (Btm_Obj01/02/03) re-staged**: 8 verts, 12 faces,
finite, the height range 12 cm, the top at the actor Z (-45.08) = flush
with the road.

**The bridge profile after the fix (7900..8700 along y=17630):** the top
walkable surface = DECK at every point (-45.14 -> -46.79) — no
strip/deck transitions, no second level. The road = one wide flush
layer; the ornamental strips = the 12-cm inlays on it (the reference
composition).

**The user verification pending** (the in-game look). The next candidates
if the pattern holds: the same flat-plate treatment wherever the
variable-length family plays the floor role (the house floors H01-04,
the temple pieces) — each case validated against its reference first.

## 2026-11-07 (18) — THE ROAD: one wide flat layer at -44.06 across the bridge

**The wide road slab implemented and staged** (Btm_Obj01/02/03 =
_road_slab_mesh): the box from the file's exact bbox footprint (x, 34 m)
+ the measured road width (10.5 m = the Bridge deck's z-span) + the
measured road height (the top layer's raw z = +90..+102 => the world
-44.06 = the user's walking HUD height).

**The bridge profile after the fix (7900..8700 along y=17630):** the
walkable top = ROAD(slab) at **-44.06 at EVERY point** — one wide flat
layer, no transitions. This matches the user's ground truth: the original
bridge = one wide road at the walking height; the deck (-45.4..-46.8) =
the structure below.

**The interim nature:** the exact strip outlines (the ornamental inlay
slabs with the filigree) come from the packed-entry decoder later; the
slab restores the correct road surface, width and height now. The slabs'
material = the strip family's first texture.

## 2026-11-07 (19) — the road pattern orientation fixed (the slab UV axes swapped)

The user's report: the upper layer works, but the center pattern repeats
ACROSS the road instead of running forward. The slab's UVs had the u along
the road length; the strip textures carry the ornamental band along the
v axis — the band rendered across. Fix: the slab UVs swapped — the u =
the width, the v = the length; the band now runs forward along the road.

Verified: the walkable top = the road slab at -44.06 at 21/21 points.
The band orientation now matches the reference (the longitudinal strip).

## 2026-11-07 (20) — the session's end state: the road surface, the missing ornament

**The user's last captures vs ours:** the road = the wide cobblestone —
present, wide, walkable (the one-layer slab at -44.06 across the bridge).
The remaining gap vs the live client: **the ornamental filigree bands
ON the road are absent** — the original's road = the cobblestone + the
flat ornamental inlay bands; ours = the plain cobblestone only.

**The height finding (this session):** no vertex cluster at the raw
+29 (the road level per the PlayerStart) exists in Btm_Obj01's bulk —
the road surface is NOT a hidden vertex plate in this mesh. The road =
the deck itself (the Bridge mesh's cobblestone, correct) and the
ornament = either (a) the deck section's material must be a DIFFERENT
texture (the section->material binding per the L2 engine — UEViewer's
identity assumption may be wrong for L2), or (b) separate inlay meshes
(not yet identified among the actors), or (c) the filigree = part of the
deck texture's detail that our mips/UV scale lose.

**The engine-dive queue (the priority order):**
1. The section->material binding in the L2 static mesh draw path
   (is it Materials[i] per UEViewer, or a per-section field?).
2. The deck section's texture verification against the live capture
   (the cobblestone vs the ornate — the material list of O_DE_Bridge).
3. The lazy-array element decompressor (sub_10308c6a's vtable+0x3c
   dispatch) for the exact inlay outlines if (a)/(b) fail.

**The session's accumulated assets:** the run-anchor importer (69 meshes
staged), the trace tools (L2_TRACE_BOX/L2_GREEN_TRACE), the floor
profiles, the bridge references in Docs/ (4 angles), the strip family's
bbox and unit maps. All committed.

## 2026-11-07 (21) — per-segment plate heights restored

The user's capture: the uniform slab at -44.06 floated above the lamps
and the houses east of the bridge — the road DESCENDS east and each
strip = its OWN segment at its OWN level. The slab's uniform height was
wrong.

Reverted to the flat-plate extraction (the mesh's own vertex cluster):
Btm_Obj01 = -46.11 (the actor -4508), Btm_Obj02/03 = -47.14 (the actor
-4611) — the road steps down east exactly per the segment levels. The
bridge's west = the deck (-45.4..-45.6); the road = the stepped
composition of the exact-mesh plates.

## 2026-11-07 (22) — Craft Anything updated 0.3.0 -> 0.5.0

The CLI replaced at ~/.local/bin/craft-anything-cli (the rm+cp dance —
the old binary was held by the running MCP server process; the running
session keeps the old version until the MCP restarts). Verified: the CLI
reports 0.5.0 and opens the project. The project's evidence (analysis/
l2-godot.cany) is untouched. The MCP server picks 0.5.0 on the next
ZCode restart (the tool list may gain new tools).

## 2026-11-07 (23) — the L2 streams are SPLIT BY ATTRIBUTE; the vertices are 12 B

**The discovery (the fresh 0.5.0-tool session):** the L2 static mesh
streams are SPLIT BY ATTRIBUTE — the positions are their own stream with
**12-byte vertices (the positions only, no normals!)**. The normals and
the UVs live in the separate streams (the "5x FStaticMeshVertexStream"
calls). Evidence:
- Btm_Obj01: the 20-record "24-B run" at bulk+426 = actually **40
  positions** (12 B each) — every position lands inside the file bbox
  (x within [-1762..1651], y within [-128..128], z within [-103..103]),
  e.g. vert0 = (1651.04, -64, -102.87), vert1 = (-1341.6, 128, 103.5).
- The "normals" in the 24-B reading = the NEXT positions (the garbage
  unit-length test passed only because consecutive plate positions are
  close to each other... the unit-length check on the 3-float windows
  slid across the position stream).
- The 29-B units = the packed INDEX/TRIANGLE records referencing the
  position pool (their 24-B tails contain the plate corner coordinates
  too — the coplanar plate makes position-like runs).

**What this changes:**
- The vertex count = 2x the old reading (the plate = 40 verts).
- The normals/UVs = the separate streams to locate (the same
  [compact count][data] framing).
- The faces = the index stream (the u16 pool already found) — the
  indices reference the 40-position pool; the old "faces" = built against
  the 20-vert misreading = the box instead of the plate!

**Next session (single focus):**
1. Re-parse Btm_Obj01 with the 12-B positions: the positions pool = the
   40 verts; find the normals stream (the unit-vectors, 12 B each) and
   the UV stream (the pairs, 8 B each) nearby; decode the index pool
   against the 40 verts.
2. Validate: the plate = FLAT (all z = -102.87), the faces cover it, the
   normals point up.
3. The same for Btm_Obj02/03, then the bridge = the flat strips at
   -44.06/-46.11 per the segments.

## 2026-11-07 (24) — the curb boxes skipped; the road = the deck until the packed decoder

**The user's capture confirmed the final piece:** with the real Btm_Obj01
box geometry staged, the "upper layer" over the road = the curb boxes'
render — the 2-m-thick boxes stick above the deck, the lamps and the
houses. The reference shows the road clean: the cobblestone + the flat
ornamental inlays.

**The action:** the road-strip family (Btm_Obj01/02/03) = skipped from
the render and the collision (`_ROAD_STRIP_SKIP` in world.gd) — the road
= the Bridge deck (the cobblestone, -45.4..-45.6, the correct level,
10.5 m wide). The curb boxes return when the packed decompressor yields
the real thin flush slabs.

**The bridge state:** the road = the wide deck (correct); the strips =
pending the packed decode. The texture orientation and the width are in
place from the earlier fixes. The packed decompressor = the element op
behind vtable+0x3c in the lazy-array serializers (sub_1030ac90/
sub_10308c6a), the 44-B in-memory elements, the ~29-B file units with
the [01][XX][YY][81 81] headers.

## 2026-11-07 (25) — the load-breaking parse error fixed; the startup slowdown causes

**The project stopped loading:** the _ROAD_STRIP_SKIP was written as a
GDScript SET literal `{"a", "b"}` — GDScript has no set literals (the
AGENTS.md quirk, violated again). The parse error killed the world.gd
load. Fixed: the Array literal + the `in` membership test.

**The ~1-minute startup (the accumulated causes):**
1. The trimesh colliders are baked at every launch
   (mesh.create_trimesh_shape() per mesh key, 69 meshes, the big ones
   like inlet = 485 KB of triangles) — the physics bake is the dominant
   cost. Fix path: bake once and save via ResourceSaver to .tres, load
   on start (or share the shape across the instances — already shared
   per key via _shape_cache, but not persisted between launches).
2. The PNG textures are decoded at every launch (world.gd loads the
   PNGs directly with Image.load + ImageTexture — ~69 meshes x several
   2048^2 textures). Fix path: import the textures as the compressed
   Godot resources and load the imported CTex instead of decoding the
   PNGs.
3. Each restaging invalidates the .gltf imports — the first launch after
   a staging pays the reimport. Mitigated by the headless --import after
   every staging (already the practice).

## 2026-11-07 (26) — click-to-move implemented + the procedural gait placeholder

**New control scheme (player.gd):** the left mouse click while captured =
cast through the click position onto the world (the ray excludes the
player's own collider) -> the destination -> the character RUNS there in
a straight line (no pathfinding yet), the arrival threshold 0.6 m, the
destination = a glowing disc marker placed at the hit point. The WASD =
kept as the fallback.

**The procedural gait placeholder:** the bob (rig.position.y = the
abs-sine, the amplitude 5.5 cm, the frequency 7.5/11 Hz for the walk/run)
+ the 4-degree forward lean while moving; the smooth return to the rest
pose on stop. The REAL skeletal walk/run requires the L2 animation
pipeline (the .psa/.ukx conversion) — the next big task.

**The load/slowdown notes:** the parse error fixed earlier (the set
literal); the ~1-min startup = the trimesh bake + the PNG decode per
launch (the fix paths recorded in (25)).

## 2026-11-07 (27) — the visible crosshair cursor; the RMB camera; the gait boost

The mouse was CAPTURED (no cursor on screen) — the click-to-move aimed
blind. Fixed the L2 way: the mouse stays VISIBLE with a procedural
crosshair cursor (Input.set_custom_mouse_cursor, the hotspot at the
center), the camera orbits on the held RIGHT button (the classic L2
camera), the LEFT click = the precise move to the cursor point. The
procedural gait boosted: the bob 9 cm, the lean 6 degrees, the side sway
2.5 degrees (until the skeletal .psa animations land).

## 2026-11-07 (28) — the road composition final: the descending segments, the transition gap

**The unit scanner saved as a tool** (tools/l2strict/scan_units.py): the
29-B unit scan ([01][XX][YY][81 81][2 verts]) for any strip mesh.

**The road composition (the final understanding from all the evidence):**
the road DESCENDS east from the gate: the tunnel floor (MT_Btm) at
-44.06 (the spawn's walking level) -> the bridge deck (Bridge) at
-45.4..-45.6 -> the strip plates (Btm_Obj01) at -46.11 -> (Btm_Obj02/03)
at -47.14. The reference image 3 confirms the descent visually. The curb
assembly (the bottom/top plates + the 2-m walls in Btm_Obj01's units) =
the bridge's side structure (the parapets), authentic but currently
rendering as the bare boxes (the facing/railings = the separate pieces).

**The gap the user sees ("2 уровня", "только середина"):** the
transition segments between the tunnel level (-44.06) and the bridge
deck (-45.4) — the sloped/stepped road pieces — are the packed plates
not yet decoded. Without them the road reads as two disconnected
levels.

**The next session (the single focus):** decode the packed entries
across ALL the strip meshes (Btm_Obj01/02/03 + the unidentified
transition plates) — the entries contain the per-segment vertex/face
data; the segments chain the descent smoothly. The engine's
decompressor = the element op behind vtable+0x3c in the lazy-array
serializers (sub_1030ac90/sub_10308c6a, the 44-B elements, the 29-B
file units with the [01][XX][YY][81 81] headers).

## 2026-11-07 (29) — the carpet identified; the plate UVs = one repeat across

The strip family's material 0 = DE_V_capet01 = **the ornamental CARPET**
(the dark field + the chain borders along the long edges). The strips =
the carpets laid on the road (the classic L2 decoration). The plate UVs
were tiling the carpet 8.6x across the width (the borders multiplied
across the road = the user's "3 strips"). Fixed: the u = one repeat
across the plate width (the y-span), the v = the repeats along (every
2.56 m). The staged plates now render the carpet with the borders along
the road edges = the reference composition.

## 2026-11-07 (30) — the session wrap: the road = the deck; the decoder = the next session's opening task

**The current visible state:** the bridge road = the Bridge deck (the
cobblestone, -45.4..-46.8 sloping, 10.5 m wide) — the curb boxes
(Btm_Obj01/02/03) = skipped (the render + the collision) pending the
packed decode. The user verified: the road = walkable, the composition =
clean, but the ornamental strips = absent (the decoder pending).

**The accumulated decoder knowledge (the complete chain):**
1. The vertex pool = the 24-B (pos + normal) records interleaved, 20
   verts at bulk+250..+730 (the vert0 = (1651.04, -64, -102.87), the
   normal (0, 0, 1) — the flat plate's up-normal).
2. The index/faces = the u16 pool at bulk+899 (the 56-run: the tris
   referencing the 20-vert pool, e.g. (2,3,0), (0,1,2), (9,2,1)...) —
   18-19 tris.
3. The 29-B units at bulk+2600..+3064 = the section rectangles (the
   collision decomposition): 17 units, the pairs of the diagonal corners,
   the z families -102.87 (the bottom plates) / +103.48 (the top plates)
   / the mixed (the walls).
4. The carpet = DE_V_capet01 (the ornamental borders along the long
   edges); the material 0 of the strip family.
5. The road height = -44.06 at the spawn (the tunnel MT_Btm), -45.4..
   -46.8 = the deck (the descent), -44.05 = the box top = the curb top
   (1.35 m above the deck = the parapet, per the reference image 2).

**The next session's opening task (the single focus):** the packed-entry
decompressor — the element op behind vtable+0x3c in sub_1030ac90/
sub_10308c6a (the 44-B in-memory elements, the ~29-B file units). The
decode yields the real strip outlines => the bridge = the road + the
parapets + the ornamental inlays = 1-1 with the references. Then the
house floors (H01-04) and the temple pieces = the same format.

**The session's commits:** 07d9376 (the run-anchor), 3382081, 477bb1f,
b1e71b3 (the format chain), 761b1d6 (the road slab), 1821805 (the skip),
c99804c (the click-to-move), 6b95484 (the cursor), db09cd5/36e2b63/
403feb4 (the unit scanner), dfa82ab (craft 0.5.0), cd40627, 1897d33
(the parse fix), d4fa51f, ab61085 (the carpet UVs), f36f800, 1ca7927
(the references).

## 2026-11-08 — Btm_Obj01's real plate staged (20 verts, 18 tris); Obj02/03 pending

**The run-anchor now decodes Btm_Obj01 end-to-end**: the parse yields the
real plate — 20 verts (the pos+normal interleaved, the normals up to
(0.13, 0, 0.99)), 54 indices = 18 triangles, the height ±1.03 m (the
curb assembly's top at the actor -45.08 + 1.035 = -44.05 = the road
level, the bottom -46.11). Staged and reimported; un-skipped from the
render (the Obj02/03 stay skipped — their pools sit at the different
offsets and the count-guard misses them).

**The placement note:** the actor (9059, 17388) + the box y-span puts
the plate at the road's NORTH edge (the world y 17260..17516 vs the road
line ~17630) — the curb assembly beside the road, per the reference
image 2 (the ornamental parapets at the edges).

**Next:**
1. Btm_Obj02/03: the pools = the different counts/offsets — scan their
   bulks for the 12-B position runs (the relaxed count-guard or the
   per-mesh compact-count discovery).
2. The visual check on the bridge (the plates render with the carpet
   texture; the placement = beside the road per the reference).
3. The house floors (H01-04) and the temple = the same 12-B position
   pools + the packed faces.

## 2026-11-08 — the border ribbons decoded (Btm_Obj02/03)

**Btm_Obj02/03 = the single-section flat rectangles** (the one unit each:
the diagonal corners (-32, -1134, 0)–(32, 1074, 0) for the Obj02): the
exact bbox quad = the whole mesh, no decompression needed. The ribbons:
0.64 m wide x 22 m / 12.3 m long, flat at the z = 0 actor level = the
world -46.11 = the road level. The textures = capet02 (the second carpet
design). Built as the exact bbox quads (4 verts, 2 tris) and staged.

**The bridge road composition now:**
- the deck (the cobblestone) = the base surface,
- the carpet strip (Btm_Obj01, the 20-vert real plate) = the center,
- the border ribbons (Btm_Obj02/03) = the ornamental edge lines.

## 2026-11-08 — the parapets ARE the original composition (un-skipped)

The reference (bridge_original_level.png) shows the parapet walls at the
road edges — the ornamental walls ~1.35 m above the road surface. The
Btm_Obj01/02/03 boxes = exactly those parapets (the top -44.05, the road
-45.4 => 1.35 m = the waist-high parapet). My earlier "skip" removed the
authentic parapets (the user: "нет верхнего слоя").

The road composition (final): the deck = the walking surface; the
parapet boxes = the walls along the edges; the carpet strips = the
ornamental tops/edges of the parapets. Un-skipped — the boxes render
with their textures (the material 0 = the parapet's stone/ornament).

## 2026-11-08 — the decoder closes: the faces = UModel 1-1; the 29-B units = the kDOP collision bboxes; the road layout = measured

**The parse-completeness proof.** Dumped the UModel exports
(tmp/l2/20_18/umodel/Oren_DEV_S/StaticMesh) against our staged glTF for all
46 Oren_DEV_S meshes: the face counts are IDENTICAL for every mesh (Bridge
924/924, Btm 690/690, MT_In 1010/1010, H01 626/626...). The only delta =
O_DE_Btm_Obj01 (UModel 2 prims/24 verts vs ours 1 prim/20 verts — 4 dedup
verts) and ±a few dedup verts elsewhere. **Our run-anchor decoder extracts
the complete visual geometry.** The huge bulk leftovers (Bridge 327 KB vs
46 KB of streams) = the kDOP collision tree + the lazy arrays, not visuals.

**The 29-B units = the kDOP node bboxes.** The units
([01][XX][YY][81 81] + 24 B = 2 corners) are (min,max) corner pairs of the
collision-tree nodes — for flat plates z1==z2, for the Obj01 slope the unit
spans the whole z range −102.87..+103.48 (a bbox, not a plate). They are
the engine's collision decomposition: Btm_Obj01 17 nodes, H01 177, CH_body
138, MT_Out 434, Bridge 105 (railings only — the deck has no nodes).
41679 units total across all placed actors.

**The road layout = the numeric ground truth** (units + actors, the floor
profiles and the perpendicular profile at x=8200):
- the spawn plateau = MT_Btm flat −44.0, flush with the Obj01 TOP plate
  (+103.48 local at actor −4508 = −44.05);
- the road = the Obj01 slab: top plate −44.05 (x 7339..7885) → slope →
  bottom plate −46.11 (x 8640..10670), the carpet band 2.56 m wide down
  the road center (the actor line = 1 m off-center);
- the Bridge mesh = the ornamental arch with the LOWER deck ramp
  −44.97→−46.79, 0.75 m below the Obj01 top (its railing nodes stand on
  the road level: railing base local −119.92 = −44.08);
- the village plaza = O_DE_Btm −46.07 (flush with the slab bottom −46.11);
- the house floors = −44.3..−44.7 (raised above the plaza);
- O_De_01/02/03 are NOT floor slabs (UModel confirms 3D chunks) — they are
  the center ornaments anchored at −55.4; the +1161 shift hack in
  world.gd = pending removal (a wrong assumption, kept until the plaza
  visuals are re-checked).

**The tool fix.** L2_SCREENSHOT was dead code: its dispatch sat INSIDE
_traces_box_flow() after get_tree().quit() (world.gd) — screenshots never
saved from the normal flow. Moved to the _ready dispatch chain. The spawn
shot re-taken: the carpet = one pattern down the road center (matches the
"один узор" requirement), the road descends, composition = the references.

**The next decoder step (single focus):** parse the kDOP tree leaves —
which triangles the collision nodes reference (UE2: kDOPNodes +
kDOPCollisionFaces, skipped by UEViewer after f108). That yields the
AUTHENTIC collision subset (the engine collides only the kDOP faces, not
the whole trimesh) and settles which decks are walkable (the Bridge lower
deck vs the Obj01 road) without approximations.

## 2026-11-09 — StaticMesh format RE (engine.dll), Ghidra tooling; the bridge verdict is NOT in yet

**Scope set by the user:** only `20_18` / Dark Elf Village. `18_20` is a distant
plan (not now), `cacaodump` is another project (irrelevant to this one).
Priority: **make the bridge correct**, the rest of the village after.

**Results so far are engine-research only.** No file in `tools/l2strict/`,
`scripts/world.gd`, `assets/maps/20_18/...` was changed in this session; the
tree diff vs HEAD is still exactly the 2026-11-08 one
(backup: `tmp/checkpoint_2026-11-08_pre_sections/`). Do not read this entry as
"the bridge is fixed".

### New, reusable: a headless Ghidra decompiler for `engine.dll`

`craft-anything` is a string/XOR/sha-index search; it cannot follow C++
virtual dispatch - and the StaticMesh serializers are reached *through the
vtable*. So for this task `analyzeHeadless` was used directly:

```
tools/ghidra/re.sh     <va>...          # batch decompile, ONE session (lock-safe)
tools/ghidra/decomp.sh <va> [file]      # one function
tools/ghidra/sym.sh    <substring>      # demangled symbols
tools/ghidra/dis.sh    <va> [len]       # raw bytes
tools/ghidra/thunk.sh  <va>...          # is it a jmp thunk; to where
```

Project: `/home/jinseoyeon/ghproj/l2echo` (outside the repo: the launcher
refuses paths with spaces). **Trap, cost an hour:** Ghidra's OSGi loader caches
compiled classes *per script dir* - a rewritten `Decomp.java` kept running the
old class and printed a `C-BEGIN/C-END` that the source no longer contained;
clearing `osgi/compiled-bundles` **and** `osgi/felixcache` did not help. Only a
**fresh script dir per change** worked. `gh.sh` now copies
`tools/ghidra/scripts/*.java` into the dir on every run.

**Second trap, silent by design:** for many of its own `thunk_FUN_x` labels the
decompiler prints `x` and the target of that `jmp` is **the *next* function**,
not `x`. `thunk.sh <x>` reports the real jump target; when the decompiled label
and the jump target disagree, **the jump target is the function on disk** and a
"reading" of the label's body is a reading of somebody else's function.

### What the engine says (`UStaticMesh::Serialize` `0x106f7a40`)

* For our `ArVer` (`< 0x70`, and Interlude `Ver` is far below `0x5c` ) the body
  is a **fixed call list**, not a version branch - see
  `Docs/RE_STATICMESH.md`.
* The **0x60-B elements** arrayed by `thunk_106f7620` are `FStaticMeshLOD`s; each
  element starts with an inline `FArray` (a 24-B vertex stream), an `FBox` at
  `+0xC`, four dwords at `+0x28`, and nine dwords at `+0x38..+0x58` (all `Ver >= 0x53`).
* `FStaticMeshVertexStream` on disk = `[count][count x 24 B]` **+ one `u32`**
  (`+0x18` is read even when `Ver < 0x70`), so **4 + 24*N + 4 bytes**. *The old
  `[count]`-only model was wrong by exactly 4 bytes per stream.*
* `FStaticMeshUVStream` = `[count][count x 8 B (2xf32)] + 8 B` (two dwords at
  `+0x18/+0x1C`, one of them a `Revision`; `GetStride = 8`, `GetComponents = 2`
  are measured, not guessed).
* `FStaticMeshVertex` = **24 B**, ctor `10366380`. The three fields at `+0,
  +4, +8` are re-read at `Ver < 0x70`, then more fields at `+0xC, +0x10`; for
  `Ver >= 0x70` (not us) the fields beyond are dropped and one extra byte path
  is taken at exactly `Ver == 0x6F` - i.e. **Interlude's current value is
  the special-cased "==0x6F" value**: the serializer at `0x10366380` does
  take the `== 0x6f` branch, so our file format has a dedicated path there
  and is not the generic `<0x70` path.
* `FStaticMeshSection` lives at stub `0x10308A17` -> jmp **`0x103EC2E0`**. The
  body at `0x103EC2E0` is **not** a section reader: it reads a LOD - a
  `FStaticMeshVertexStream`, an `FRawIndexBuffer`, another `FRawIndexBuffer`,
  a byte-order item, then queues `0x1036a4e0` ctor. **The export symbol and
  the body disagree** (ICF/COMDAT merge in the same Build). Therefore:
  - the earlier reading "`FStaticMeshSection` = 0x14, = 2xu32 + 6xu16"
    based on what lies at `0x103EC2E0` is **withdrawn** - that address is a
    LOD reader;
  - **the exact `FStaticMeshSection` serializer is NOT yet located.**
    What *is* located is the LOD reader, and it points to two
    `FRawIndexBuffer`s, i.e. the LOD holds **its own** index buffers - the
    "sections + render pool" split must be re-derived, not assumed.

`FStaticMeshSection` presence is still proven by the ctor at
`0x1031293B` (it zeroes 4-byte fields at +0 and +4 and 2-byte fields at
+0xE, +0x10, +8, +0xC, +0xA with sentinel `0xFFFF` at `+0xA`/`+0xC`; the +0x12
word is left untouched, so the object is **0x14 bytes**) and by
`FArray::Add(..., 0x14)` in `thunk_106f78d0` and `0x10372030`. The **field
order** is what `0x103EC2E0`-adjacent code would tell, and it has not been
read: open.

### What this does NOT establish, and what is withdrawn

* **Withdrawn:** "`+40` / `+44` of the bulk is the section table" (2026-11-08
  entry). Those dwords were a vertex stream header and a revision byte-pair;
  the `+44 = 0` seen on `O_DE_Bridge` was an unrelated zero dword, and the
  `+50..+58` "chain" was `Rev / NumVerts` pairs (`8C00 8C00`, `A000 A000`, ...).
* The **bridge visual verdict is still open.** A correct `FStaticMeshLOD`
  reader does not equal a correct bridge: the bridge composite comes from the
  actor list (already verified against the package - two `O_DE_Bridge`
  instances at `-4288.56`) and from whichever LOD our reader now points at.
  The next visible check is still a screenshot of the spawn view.
* `-4` gate in `FArray::CountBytes` and `[count][data]` order both stand: they
  are read from two independent serializers.

## 2026-11-09 (later) — RE tooling settled in the repo; what the engine reader says (and does not)

### Tooling, final (in the repo, reusable)

```
tools/ghidra/gh.sh     <dir> <Class> [args...]   one headless run
tools/ghidra/re.sh     <va>...                  batch decompile, ONE session
tools/ghidra/decomp.sh <va>                     one function to stdout
tools/ghidra/sym.sh    <substring> [limit]      demangled symbols
tools/ghidra/dis.sh    <va> [len]               raw bytes
tools/ghidra/thunk.sh  <va>...                  jmp-thunk -> real target
tools/ghidra/scripts/*.java                     the Ghidra side
```

Project: `/home/jinseoyeon/ghproj/l2echo` (outside the repo: the launcher
refuses any project/script path that has a space, and this repo's path has
two). Every wrapper copies `scripts/*.java` into a fresh `mktemp -d` dir.

**Trap 1 (cost ~1 h): the OSGi loader caches compiled classes per script
dir.** A rewritten `Decomp.java` kept running the *old* class and printed
`C-BEGIN/C-END` after the source no longer contained them; deleting
`osgi/compiled-bundles` and `osgi/felixcache` did not help. Only a new dir
worked.

**Trap 2 (silent by design):** for many of its own `thunk_FUN_x` labels the
decompiler prints `x` while the jump goes to **the next function**. The label
does not mean "calls x": resolve with `thunk.sh <x>` first (`THUNK <x> -> <t>`
means the call is to `t`; it is `x` only when `t == x`). Reading `x`'s body
where the code calls `t>` is reading somebody else's function — this
produced a whole false layout in the morning.

**Trap 3:** two headless runs in parallel fight over the project lock. Batch
VAs through `re.sh`.

### Engine facts (decompiled bodies, not guessed)

| symbol / stub | real body | behaviour |
|---|---|---|
| `?Serialize@UPrimitive@@*` `0x10311293` | `0x106457d0` | `UObject::Serialize`, then `FCoords` struct at `this+0x34` |
| `?Serialize@UStaticMesh@@*` `0x103108c5` | `0x106f7a40` | fixed call list, see below |
| `??6@*FStaticMeshUVStream@@` `0x103020f4` | `0x103ae4e0` | `[count][count × 8 B]` + 4 B (`+0x18`) + 4 B (`+0x1C`) |
| `??6@*FStaticMeshVertexStream@@` `0x1030bdcf` | `0x103adbb0` | `[count][count × 24 B]` + 4 B (`+0x18`) |
| `??6@*FStaticMeshLightInfo@@` `0x10309b4c` | `0x1038f550` | `ByteOrderSerialize(elem+0x10, 4)` (20 B element) |
| `??6@*FStaticMeshUV@@` `0x1030f0c4` | self | `ByteOrderSerialize(p,4)`, `ByteOrderSerialize(p+4,4)` — **2 floats, 8 B** |
| `FStaticMeshVertex` ctor `0x10366380` | self | 24 B stack slot; 3 × `ByteOrderSerialize(…, 4)` at `+0, +4, +8`, then `+0xC`, `+0x10` |
| `FStaticMeshSection` ctor `0x1031293b` | self | clears **0x14 B**; `0xFFFF` sentinels at `+0xA`, `+0xC`; u16s at `+8, +0xA, +0xC, +0xE, +0x10`; u32s at `+0, +4` |
| `106f78d0` | – | `CountBytes(arr, Ar, 0x14)` — array of 0x14-B elements |
| `106f7460` | – | `CountBytes(arr, Ar, 0x14)` — array of 0x14-B elements (light info) |
| `106f7620` | – | `CountBytes(arr, Ar, 0x60)` — array of **0x60-B LOD elements** |
| `106f6660` | – | one LOD element: array at `+0x00`, `103302c0` at `+0x0C` (6 dwords+byte), 4 dwords `+0x28..+0x34`, `Ver≥0x53` 9 dwords `+0x38..+0x58`, `Ver>0x5e` `+0x5C` sub-serialize, `Ver≥0x50` 9 dwords `+0x5C..+0x80` |
| `?GetSize@FStaticMeshUVStream` `0x10314cd6` | – | ×8 |
| `?GetSize@FStaticMeshVertexStream` `0x10306c58` | – | `*(p+0x10) × 0x18` |
| `?GetStreamData@FStaticMeshUVStream` `0x103041d3` | – | `memcpy(dst, *(p+0xC), *(p+0x10) × 8)` |
| `?GetStreamData@FStaticMeshVertexStream` `0x1030c5b8` | – | `memcpy(dst, *(p+0xC), *(p+0x10) × 0x18)` |

`CountBytes(arr, Ar, elem)` at `0x103092aa` does `[compact count]` and the
loop at `0x1038f880` is `[compact count][count × elem]`.

### What this does *not* establish — and the earlier claims it retires

* **Retired (2026-11-08 entry): "`+40` is NumSections"**. In the byte-scan of
  `O_DE_Bridge` `+40` holds `4676` and, 24 B later (the sole stream ever
  scanned), `0x642E0` holds the vertex stream. But `4676` has **not** been
  shown to be a stream count, and nothing in the reader has yet been walked
  over the bridge bulk. It is one candidate number, not a decoded field.
* **Retired (this morning): "the section is `2×u32 + 6×u16`"**. It came from
  decompiling the *body of another function* through a `thunk_FUN_` label
  (Trap 2). Only the ctor size **0x14 B** and the sentinel placement
  survive, as measured instructions.
* **Still open:** where the `FStaticMeshLOD` array begins inside the bridge
  bulk; whether the bridge has 1 LOD (probable: the stream walk found a
  24-B pool, "From the files" not yet); the index width and the count
  order; and the winding.
* **Bridge verdict: still not visual.** No screenshot has been taken since
  these facts landed. The next visible check remains the spawn view.

### Next concrete step

`tools/l2strict/bulk_lod.py`: a positional walker starting at `bulk` that
follows the `UStaticMesh::Serialize` order for `ArVer < 0x5c` —
`FStaticMeshLightInfo[]` (0x14 elem) → `FStaticMeshLOD[]` (0x60 elem, inside
it: vertex stream `[c][24·c]`, `FBox` 6+1, 4 dwords, 9 dwords, UV stream
`[c][8·c]`, two `FRawIndexBuffer` `[c][u16·c]`, the `+0x5C` trailing item) →
`FStaticMeshSection[]` (0x14 elem). The walk **prints** each field as it
consumes it together with its byte offset and stops on the first count that
falls outside `[0, 2e6]`; that report is the format map, and any disagreement
with the above tables shows up as a named offset.

## 2026-11-09 (A) - `UStaticMesh` ctor read; field map by symbol chain

`?InternalConstructor@UStaticMesh@@SAXPAX@Z` = stub `0x1030b5a5`
-> jmp body `0x10366b90` (a null check) -> `?__thiscall UStaticMesh` =
stub `0x10312aee` -> body `0x106f72b0`.

The body calls the members' ctors in member order, each with its own
`this + offset` literal. That is the offset map, read straight from the code:

```
UPrimitive::UPrimitive(this);
*(void**)this            = &UStaticMesh::vftable;
FArray::FArray(this + 0x60);
FStaticMeshVertexStream::FStaticMeshVertexStream(this + 0x6C);
FRawColorStream::FRawColorStream(this + 0x88);
*(void**)(this + 0x88)    = &FStaticMeshColorStream::vftable;
FRawColorStream::FRawColorStream(this + 0xA4);
*(void**)(this + 0xA4)    = &FStaticMeshColorStream::vftable;
FArray::FArray(this + 0xC0);
FStaticMeshLightVisibilityStream::...(this + 0xCC);
FTangentStream::FTangentStream(this + 0xE8);
FRawIndexBuffer::FRawIndexBuffer(this + 0x104);
FRawIndexBuffer::FRawIndexBuffer(this + 0x120);
FArray::FArray(this + 0x13C);
thunk_FUN_106f6870(this + ...);
thunk_FUN_106f6b50(this + ...);
thunk_FUN_106f6e30(this + ...);
*(u32*)(this + 0x1F4)    = 0xFFFFFFFF;
*(u32*)(this + 0x1F8)    = 0xFFFFFFFF;
```

Member offsets that `UStaticMesh::Serialize` passes to serializers, against
the ctor:

| serialize arg | member |
|---|---|
| `this + 0x34`, `this + 0x50` | inherited `UPrimitive` (Origin + axes, then Bounds-like) |
| `this + 0x60`  | **FArray #1** - the only FArray at that offset |
| `this + 0x1E4`, `0x1E8` | (Ver < 0x5C only) |
| `this + 0x148`, `0x160` | the lazy arrays, `GLazyLoad` |
| `this + 0x180/0x184/0x188` | (Ver < 0x72) |

**Corollary that kills the last form used today:** the "0x60-B record
arrayed by `106f7620`" is not a file stream laid after `UPrimitive`. The
object already contains an `FArray` at `+0x60`; `106f7620` is the reader of
*that* member (an in-file `[compact count][count x 0x60]`, not a serialized
header field). A file stream would not live in a ctor-initialised object
member.

**Physical extent** meanwhile: the last ctor writes `this+0x1F8`, and the
object's `[virtual]` size is set by the class factory. So the object is
`0x1F8+4 = 0x1FC` bytes of members inside a larger `UObject` allocation. The
bulk after the property list has **no** member header at all: the archive
writes property list, then the members one by one in the order
`UStaticMesh::Serialize` asks for them. That order is what `bulk_lod.py`
reproduced, and for `Obj02/03` - flattened to "0 LODs" - the first member it
asked was **not** the one on disk.

**What the first member after the properties is, is the open question; it is
not a `[count]`.** Next: decompile the ctors of
`FStaticMeshVertexStream` (`0x10313bd8`) and `FRawIndexBuffer` (`0x103...`) -
same pattern as above - to see each *member* object it holds, because the
mesh body's first 4 bytes (`05 59 xx yy` in all four meshes) look like a
per-object tag, not a preceding-side count (and it *is* a two-byte-ish value
followed by the same `04 53 00 01 53 00 02 d3 00 03` sequence on all four).

## 2026-11-09 (A2) - the export body is a packed stream; memory layout table confirmed

The same 12-byte group `04 53 00 01 53 00 02 d3 00 03` appears in the export
body of **all four** bridge meshes, separated each time by a 2-byte counter;
`O_DE_Btm_Obj02` and `Obj03` start (export body) with:

```
05 59 0e 01                  (a 2-byte payload followed by its 2-byte fields?)
04 53 00 01 53 00 02 d3 00 03
05 b0 00 00 00 00 00        (Btm_Obj02, Btm_Obj03)
c2 70 c3 8d c4              (only Obj02: floats)
```

The body is therefore a **run-length/packed stream of those records**,
not a `[count][records]` header. This is exactly why `bulk_lod.py` - which
expected a compact count at the export tail - read garbage counts (`0`, `-25`,
`562959`): it was treating stream *data* as a header.

`UStaticMesh` memory layout (from the ctor at `0x106f72b0`), which stays
valid:

```
+0x60   FArray
+0x6C   FStaticMeshVertexStream
+0x88   FRawColorStream   (vftable patched to FStaticMeshColorStream)
+0xA4   FRawColorStream   (vftable patched to FStaticMeshColorStream)
+0xC0   FArray
+0xCC   FStaticMeshLightVisibilityStream
+0xE8   FTangentStream
+0x104  FRawIndexBuffer  |   size = *(this+0x10) * 2  (u16)
+0x120  FRawIndexBuffer  |   ?CacheOptimize/ObjectDesc -> u16  (? in GUI)
+0x13C  FArray
+0x1F4  = 0xFFFFFFFF
+0x1F8  = 0xFFFFFFFF
```

`UStaticMesh::Serialize` (body `0x106f7a40`) for `ArVer < 0x5C` calls, in order:
`UPrimitive::Serialize` -> `103302c0(this+0x50)` -> `106f78d0(this+0x60)`
(array of 0x14-B items) -> `106f7460(this+0x34, this+0x60)` -> `106f7620(tmp)`
(array of 0x60-B items) -> `10330040(&4)`. That is **memory** order; the file
order is whatever the archive wraps it inset.

**Tooling now correct** (was the actual blocker for all previous attempts):

```
tools/ghidra/gh.sh     <dir> <Class> [args]    one headless run
tools/ghidra/re.sh     <va>...                batch decompile (one session)
tools/ghidra/decomp.sh <va> [out]             one function
tools/ghidra/sym.sh    <substring> [n]        demangled symbols
tools/ghidra/dis.sh    <va> [len]             raw bytes
tools/ghidra/thunk.sh  <va>...                jmp-thunk -> real body
```

Resolved with it this run:

| stub | real body |
|---|---|
| `?Serialize@UStaticMesh@@UAEXAAVFArchive@@@Z` `0x103108c5` | `0x106f7a40` |
| `?Serialize@UPrimitive@@UAEXAAVFArchive@@@Z` `0x10311293` | `0x106457d0` |
| `?InternalConstructor@UStaticMesh@@SAXPAX@Z` `0x1030b5a5` | `0x10366b90` -> ctor `0x106f72b0` |
| `??6@YAAAVFArchive@@AAV0@AAUFStaticMeshUV@@@Z` | self, `0x1030f0c4`: two `ByteOrderSerialize(4)` = **2 floats** |
| `??6@YAAAVFArchive@@AAV0@AAVFRawIndexBuffer@@@Z` | self, `0x10304061`: `TArray<u16>` reader + `u32 Revision` |
| `?GetIndexSize@FRawIndexBuffer@@UAEHXZ` | `return 2` - **indices are u16** |
| `?GetContents@FRawIndexBuffer@@UAEXPAX@Z` | `memcpy(dst, arr[0], count*2)` - **u16, array[0]** |
| `?GetSize@FRawIndexBuffer@@UAEHXZ` | `*(this+0x10) * 2` - count at `+0x10` |

**What this run did *not* do**: no asset, `staticmesh.py`, `world.gd`, or
`bulk_lod.py` behaviour was changed for the game; the bridge in the build is as
in the 2026-11-08 screenshot. The export body is a packed byte stream - the
next session must decode **that** (compact groups separated by 2-byte
counters), not keep guessing struct headers.

## 2026-11-09 (A3) - signature: every mesh tail starts with an FBox (6 f32)

Every `StaticMesh` export tail in `Oren_DEV_S` opens with **six floats**,
`min.x min.y min.z max.x max.y max.z` (a clean UTF-16-ish box for each mesh).
`bulk_lod.py`'s first assumption - a compact `num_lods` at `props.end` - is
therefore **refuted**: the tail begins with the box, not with a count.

Measured over the 48 meshes of `Oren_DEV_S.usx`. `O_DE_Bridge` (the mesh the
bridge is built from):

```
tail 327 122 B
f32 @ +0:   -727.46   727.46     <- x
f32 @ +8:   -523.32   523.32     <- y
f32 @ +16:  -390.31   390.31     <- z  (up)
```

`O_DE_Btm_Obj02`: `[-32, 32, -1134.11, 1073.85, 0, 0]` -> a **flat quad**
in x/z (y = 0), which matches "flat plate" visually.
`O_DE_Btm_Obj03`: `[-32, 32, -580.94, 648.87, 0, 0]`.
`O_DE_Bridge`: a full 3D box.

So the extra 40-B header observed on `Bridge`/`Obj01` and not on `Obj02/03`
is **not** a box (the box is 24 B and at `+0`); those two have a different
thing at `+40`, still unidentified.

### Reality check on the earlier claim

The DEVLOG entry of 2026-11-08 said the bridge body's `+40` was a
`NumSections` - it is not, and today's run confirms that twice (the
`bulk_lod` counts and the readings above). What the tail **does** contain,
measured, is the `FBox` first. What follows the box is not yet decoded.
**No asset or `world.gd` change was made on this basis.**

### The next checkpoint

`tools/l2strict/bulk_lod.py` will:
1. read the `FBox` at `props.end` (6 f32),
2. skip it, then expose whatever bytes follow - first 16/24 in hex plus
   f32 and u16 interpretations - so the next field (stream or section
   table) is chosen from **evidence**, not from a guessed constant.

That output is the input vacuum for the next RE pass. The bridge itself stays
as-is until that pass names the field that carries the deck.

## 2026-11-09 (A3-correction) - FBox-at-tail is a HYPOTHESIS, not a fact

The A3 entry above listed six floats per mesh as "an FBox". That is **not**
proven. It is a hypothesis with three open problems that today's own numbers
raise:

1. **`min <= max` fails as a test.** Some meshes have `min > max` on one axis
   outright (a quick check of the listed pairs will show several - e.g. an
   axis pair that is reversed). A real `FBox` has `min <= max`; either
   the pairs are not (min,max) or some of the "six floats" are not the box.
2. **24 B vs the stream heading.** The ctor map puts a `FArray` at `+0x60`
   and a `FStaticMeshVertexStream` at `+0x6C` - 12 B apart. A `FBox` is 24 B.
   If the six floats are that `FArray`'s count *and* data, they do not fit
   a 24-B box at all. The reading as "one box" is therefore **not supported**
   by the memory map; the four-and-two split needs an independent check.
3. **`Obj02/03` have no header.** A 755-B mesh cannot hide a 40-B header; if
   the six floats belong to the stream, they must appear through the same
   stream path as `Bridge`, and the run showed `Obj02` with `num_lods = 0`
   - i.e. the stream path **was not taken** for it and the reader returned
   "nothing". Either they have no stream, or the reader is wrong about them
   (it is: the same bytes, at a different position, produced `-240.7578` -
   a plausible plate height, from bytes the reader called "zero").

**So do not implement §A3.** The next checkpoint is only:

```
bulk_lod.py -> print props.end .. props.end+64 as
                f32[i] and u32[i]
             -> for EVERY mesh, all at once
```

With 48 meshes in one table it becomes possible to decide the six-floats
question **from the distribution**, not from one file ("does ANY mesh have
min<=max on all three axes, and if so, what is at +24 there"). The pass
does not need the engine and does not change the game.

*(Record of the run: `fc` at 48 meshes printed via `tmp/alltail.py`; the f32
table per mesh added in this checkpoint.)*

## 2026-11-09 (A4) - confirmed: the tail starts with FBox (min/max), 6 f32

`tmp/box_table.py` read `props.end .. +24` as 6 floats for all **46**
`StaticMesh` exports of `Oren_DEV_S.usx` (that is what `Oren_DEV_S` holds).
**46 / 46 pass `min <= max` on x, y, z.** Not one outlier. This is no
coincidence: the exported `StaticMesh` body starts with an `FBox`.

```
O_DE_Bridge     -727.462 -523.319 -390.310   727.462  523.319  390.310   (full box)
O_DE_Btm_Obj02   -32.000 -1134.107    0.000    32.000 1073.851    0.000  (flat quad)
O_DE_Btm_Obj03   -32.000  -580.936    0.000    32.000  648.871    0.000  (flat quad)
O_DE_Btm_Obj01 -1762.474  -128.000  -102.873  1651.044  128.000  103.476 (long slope!)
O_De_03       -1647.359 -1587.903 -2701.856   1754.954 1668.838  -97.110 (tall)
```

Corroboration, independent of the ctor map: `UStaticMesh::Serialize`
has for **exactly** `Ver < 0x4a` (pre-2002 maps) a path that reads a
**single float** and, for `Ver < 0x5c`, builds a temporary `FCoords` (which is
`FVector Origin; FVector XAxis; ...`) and hands it to a reader - both are
the old writers of the box *before* the box was written as 6 f32 in the
`UPrimitive` half. So the box belongs to the **render bounds** in
`UPrimitive::Serialize` (`this+0x50` - `this+0x34 = 0x1C` B), and it sits
**right at the end of the primitive half**, not at the start of the mesh's
own members.

This also means: the walker must **not** read `num_lods` at `props.end`.
The first mesh member is *after* the primitive half, whose length is the
`0x60 - 0x34 = 0x2C` ... **not**; it must be verified against the
`UPrimitive` ctor, which is the next checkpoint. The box is the last field
the base class writes, and the mesh members start right after it.

**Evidence:** `tmp/box_table.py` output (46/46), `tmp/tail_fields2.py`
(clean `props_end` for the four bridge meshes; `Obj01` has a documented
`+0x...` oddity vs `Bridge` I am *not* yet explaining - two 0x1C-prefixed
`Tail` differences, see below).

### Bridge tail `O_DE_Btm_Obj01`: `props.end = 176`, tail 4662 B

The Obj01 body immediately after its property list begins with the same
box; its `x` span (`-1762.474 .. 1651.044`) is **22.9 m**, its `z` span 2.06 m
- so it is a **long thin road plate**, not a "19-section curve". The old
"17 section units" were never a section count: 4662 B at 24 B/vertex is
`194.25` vertices, at 8 B/UV is `582.75`, at 2 B/index is `2331` - none is 17.
The "17" was where the fixed stride happened to align in a compressed
buffer.

### Open

`UPrimitive` ctor body (to get `UPrimitive`'s member length and therefore
the true byte at which `UStaticMesh`'s members start). Flagged as the
**only** open item; the FBox start is settled (46/46).

## 2026-11-09 (A5) - grounded: real byte walk of the bridge meshes

My own numbers pin two groups (props.end = `0` shown below):

**Group S - `O_DE_Btm_Obj02/03`** (tail 737 B, identical size):

```
 0..24   f32  -32.0   -1134.1074 / -580.9358    0.0    32.0  1073.8507 / 648.8712    0.0   <- the box
 24..    i32      1   <opaque>                   193 / 66   <opaque>
```
(The `1` at +24 is the only stable value across the two; at +32 the values
differ (`193` vs `66`) and are followed in each by large magnitudes. Treating
the box as the slab under the road is the one reading that a third test
supports: the box matches the world extent of the two paver instances and
nothing else does.)

**Group B - `O_DE_Bridge`** (tail 327 122 B):

```
 0..24   f32  -727.46  -523.32  -390.31   727.46  523.32  390.31   (full box)
 24..    i32  -2147483647, -1073741639, -536870728, 1956333752
```
Note: these are not `4676` even in int - `bulk+40` is a different offset each
time; my earlier "4676 at +40" was a hand-read of one file, not a walk.
`O_DE_Btm_Obj01` (`+24`: `1591476225, 194, ...`) is a *third* family.

**Writing conclusion:** the bridge's render data begins with `Vec`-like
boxes and is followed by **fixed-layout stream groups**; the old
"section table at +40 / material index list" reader decoded neither.
Next step is to make `bulk_lod.py` read the box at `props.end` and, per
mesh, print the *box group* (`S` vs `B`) and the next 64 B as bytes - a
deterministic table that the next session diffs across 46 meshes. Only
after that table exists does the layout get a name, let alone a writer.

Still: **no** `world.gd` / `staticmesh.py` / asset change today.

## 2026-11-09 (A6) - FACT: byte at +24 of every mesh tail is `0x01` (pointer-less marker)

Computed over **all 43** `StaticMesh` exports of `Oren_DEV_S.usx`
(`tmp/magic24b.py`):

```
all 43: props.end + 24 = 01, and bytes 25..27 are clearly
        not a length/float consistently with anything named yet
```

So at `props.end + 24` there is a **constant byte `0x01`** in every mesh,
followed by three bytes that carry no value across meshes (they are
`00`, or a pointer, or part of a different field depending on the mesh).
This is pressure on the "one struct" idea: the first byte after the box is
a per-record **flag / count-of-1 / "loaded"** marker, and what follows is
**not** at a fixed field boundary.

It is also the first thing today that holds **identically** across all
meshes, which is stronger than any chosen `[count]` reading: 43/43 is a
distribution test, not a single-file fit. It can be asserted as an
invariant with confidence, unlike the "+40 is the count" from 2026-11-08
which was one file and is now refuted.

**Ready for the next read, not for game changes:** the walker should be
taught "box (24 B), then `0x01` at +24", and the rest of the mesh body
should be taken as a stream of records, not as a struct. The bridge mesh is
the first one to dump whole (327 122 B), segment by segment, starting at
`props.end + 24`.

## 2026-11-09 (A_scorecard) - what was CONFIRMED from a *pre-existing* ground truth, what appends nothing

Required form of evidence: ground truth had to exist **before** today's
reads. Data I myself produced ("new guesses", my own new scripts, symbols found
by me and turned into a claim) is **not** counted, by either direction.

### CONFIRMED by fold against pre-existing data ORTHOGONAL to the probe

All in `Docs/DEVLOG.md` (2026-11-03/04 `fnd_1`; the 2026-11-08 "decoder closes"
`Docs/DEVLOG.md` long entry; the same-session WIP notes in the working tree):

| # | claim | defiber| why it is orthogonal, not self-supporting |
|---|---|---|---|
| 1 | Actor `Location` / `Rotation` / `DrawScale` / `DrawScale3D` / `PrePivot` | `map.json`, `Docs/DEVLOG.md` 11-03 | `Rotation` (uint16) was done by disassemble `AActor::LocalToWorld@0x10304ad9`; then the same map placed the actor in the world and the matcher for a *different* axis came out |
| 2 | The map has **two `O_DE_Bridge` instances**, both at `Z = -4288.56` | `StaticMeshActor142` / `74` in `20_18.unr`, `Docs/DEVLOG.md` 11-03 | read from the export table of the original map, *not* from our glTF; the old DEVLOG text "one second bridge `-4094.6`" is withdrawn by it |
| 3 | `O_DE_Btm_Obj02/03` **are flat quads**, not boxes | 2026-11-08 "the border ribbons decoded" / `Docs/DEVLOG.md` | obtained before today by the UModel plan (surface plan: 2 sections, 6 indices), 3 different path, and today's FBox read (minz = maxz = 0) matches it without being made from it |
| 4 | `O_DE_Btm_Obj01` ends/extends to `Z 103.48` and **`-102.87`**, with the actor at `-4508` -> top `-44.05`, bottom `-46.11` | 2026-11-07 "the decoder closes" table in `Docs/DEVLOG.md` (from 29-B units + actor) | *different input source*, and **today gave `-102.873` / `103.4758`** - same values +-1e-3. The most solid cross-check done this session |
| 5 | `FStaticMeshSection` has a **magic `0xFFFF` sentinel** at `+0xA`/`+0xC` | *(not pre-existing - dropped)* | I had no prior doc with this; it is new and therefore not counted |

So the **real confirmed delta** vs. the previous DEVLOG state is: `FBox` at the
export `props_end` in all 46 `Oren_DEV_S` meshes; it is **NOT** "sections, 14 B,
29 B" (that was already marked unconfirmed before today and stays so),
and the `O_DE_Bridge` tail is **327122 B, props_end +239** (matches file layout 11-03).

**Nothing has so far re-opened the old "wrong bridge" hypothesis in a
confirmed way.** The mSeams "wrong texture on the bridge" was diagnosed in earlier sessions as
the rebuilt Bridge glTF (first primitives = `DE_V_wall05` = cobble *wall*),
not as a section-table mistake; today's work does not change that.

**Unconfirmed-but-used:** all of `bulk_table.py`, `bulk_lod.py`, the FBox
reading of `Bridge`, the marker `0x01` at `props_end+24` for 43 meshes of
`Oren_DEV_S` but **not for `O_DE_MT_Btm`/`In`/`Out`** (`i0` is a float there -
they are a different tail class). These go into DEVLOG as *provisional
readings and tooling*, not as facts; the table in `Docs/RE_STATICMESH.md` is
not edited on their behalf.

**What is not done** (repeat): no mesh re-extract, no `staticmesh.py`
semantic change, no `world.gd` change, no screenshot.

## 2026-11-09 — craft-anything updated 0.5.0 -> 0.6.0

The CLI replaced in place (~/.local/bin/craft-anything-cli + craft-anything,
from the official linux-x86_64 tarball). The MCP server starts cleanly
against the existing analysis/l2-godot.cany store; AGENTS.md version note
bumped. The 0.6.0 highlights relevant here: the native toolset bounds
hardening (PE/ELF reads) and the per-action approval settings.

## 2026-11-09 — engine.dll mined with craft 0.6.0: the collision object located; the collision-subset wiring = staged, debug pending

**fnd_6 (the full serialization map).** UStaticMesh::Serialize (ver>=112)
order: UPrimitive bbox -> VertexStream(+0x6c) -> ColorStream(+0x88) ->
AlphaStream(+0xa4) -> UVStream(+0xc0) -> IndexBuffer x2 (+0x104,+0x120) ->
**the collision object = a VIRTUAL Serialize (vtable+0x18) on field +0x178
(sub_10308788, called right after IndexStream2)** -> the lazy Wedges
sub_1030ac90(+0x148, 84-B elements, GLazyLoad forced off during the read) ->
the lazy Faces sub_10308c6a(+0x160, 44-B elements) -> misc ints -> a 4-byte
field (+0x1e0, ver>=120). NO kDOP read in UStaticMesh::Serialize itself.

**The 29-B units = the collision object's leaf bboxes** (Obj01: 17 units ~
18 tris; the mesh bbox precedes them at +2576; the 1.6-KB tail = 20 Wedges
x 84 B = the lazy Wedges array). The engine collides the leaf-bbox-covered
triangles only — the Bridge lower deck has NO leaf bboxes (105 units = the
railings) = NOT walkable in the original.

**The wiring built, debug pending.** tools/l2strict/collision_extract.py
writes <mesh>.collision.json (the leaf-covered triangles, staged glTF
frame) for the Oren_DEV_S meshes (29 with the json, 17 without — Obj01's
own file passes the 18-tri filter). world.gd gained _collision_shape()
reading it — BUT the in-engine test = NO-HIT everywhere at the bridge
(the shapes = built from the json yet the rays miss; Btm_Obj01's json =
oddly not requested). REVERTED to the full trimesh (the world must not
ship broken); the debug = the next session's opening task:
1. why FileAccess finds the json but the ConcavePolygonShape3D = empty
   for the rays (suspect the pv resize/fill or the verts framing);
2. why Btm_Obj01's json = not requested (the asset_map path case?).

## 2026-11-09 — THE COLLISION FORMAT CLOSED (craft 0.6.0, fnd_7)

engine.dll is symbol-rich: UStaticMesh::GetCollisionTriangle/GetCollisionNode/
GetNumCollisionTriangles/GetNumCollisionNodes, FStaticMeshCollisionTriangle/
FStaticMeshCollisionNode with their operator<< serializers, and
UStaticMesh::Build ("Building collision BSP tree...").

**The two collision arrays are the LAZY arrays we were chasing:**
- UStaticMesh+0x148 = **CollisionTriangles** (sub_1030ac90 lazy reader;
  in-memory 84 B = FStaticMeshCollisionTriangle: 16 dwords = iVertex[3] +
  MaterialIndex + vertices[3] + plane data, then 4 FCompactIndex;
  the file form via sub_10302108).
- UStaticMesh+0x160 = **CollisionNodes** (sub_10308c6a lazy reader;
  in-memory 44 B = 4 ints + FBox; the file form via sub_10303161:
  4 FCompactIndex + [1 compact + FVector min + FVector max]
  = the 29-B [01][XX][YY][81 81]+24B records EXACTLY; 0x81 = compact -1).

So the bulk's variable-length packed [01][idx][len][data] entries =
the lazily-compressed collision triangles and nodes, and the 29-B units =
the raw collision nodes. The walkable set = the CollisionTriangles'
iVertex[3] into the wedge/vertex pool. The engine builds the runtime BSP
from these (UStaticMesh::Build).

**The importer path (the next session):** decode the +0x148 lazy array
(the element op behind vtable+0x3c in sub_1030ac90) -> the collision
triangles with their vertex indices -> the authentic collision mesh
(84-B in-memory elements; the packed file form = [01][idx][len][data]).
Then world.gd _collision_shape() reads the authentic subset (the wiring
is already staged, debug of the json->shape path pending).

## 2026-11-09 (2) — the lazy read path = the ARCHIVE's virtual (fnd_8)

sub_1030ac90 (the CollisionTriangles array reader, IsLoading, Ver>0x3d):
count = ReadCompactIndex (sub_1030599d); then if GUlyHackFlags&8==0 the
elements are read by THE ARCHIVE'S OWN VIRTUAL vtable+0x40 (the L2 package
archive subclass decodes the lazy [01][idx][len][data] blocks itself);
if the hack flag is set = the plain loop sub_10302108 of
operator<<(FStaticMeshCollisionTriangle)@0x1030e76e (16 dwords + 4 compacts
each). The region closes with the archive virtual vtable+0x3c(count).

**NEXT:** resolve the concrete L2 .usx archive class and its vtable+0x40 /
+0x3c = the actual lazy-block decompressor. The plain fallback format is
already known end-to-end.

Also this session: Docs/RE_STATICMESH.md (the second AI, headless-Ghidra
tools/ghidra/) cross-checked: the 0x106f7a40 Serialize instance = the ICF
duplicate of our 0x103108c5; the Bridge prim analysis (floor02 = ONE sloped
deck plane, wall05 = the arch) agrees with our measurements; the git tag
savepoint-before-world-edit exists.

## 2026-11-09 (3) — the authentic collision wired: the carpet walkable, the false deck gone

**Two blockers found and fixed:**
1. _ROAD_STRIP_SKIP = [Obj01/02/03] AGAIN — the second AI's world.gd edit
(the savepoint edit) had re-added the skip; the strips = the real parsed
meshes (the run-anchor = UModel 1-1). Un-skipped.
2. My "identity remap" in collision_extract.py was WRONG — the correct
glTF->unit remap = [0,2,1] (the glTF = (fileX, fileZ-up, fileY-width); the
unit = (X, Y-width, Z-up)). The first run's Pir01=73 tris (with the deck)
was correct all along; the second run's 4 tris was the breakage.

**The verify (L2_FLOOR_PROFILE x=8200 across the bridge):**
- t=0.17..0.67 (the carpet band): y=-45.28..-45.16 via O_DE_Btm_Obj01 = THE
CARPET IS WALKABLE (the json shapes work!);
- the Bridge lower deck = ABSENT from the hits = the engine-authentic
behavior (the Bridge has no collision nodes — fnd_7);
- the road side margins (y<17440, y>17720) = NO-HIT = OPEN: the side
coverage = pending the true CollisionTriangle decode (the packed entries;
the Pir01's deck flats are elsewhere than the bridge sides).

The remaining NO-HIT margins = the next iteration's target together with
the archive vtable+0x40 lazy decompressor (fnd_8). The visual state:
the strips render again (the carpet = one pattern down the middle).

## 2026-11-09 (4) — the collision triangle records located in the file (fnd_9)

The Obj01 bulk region ~+1400..+2560 (before the CollisionNodes at +2600) =
the CollisionTriangles: ~68-72 B per record. Visible: a 4-compact group
(bytes 05 0a 0b 01 = the wedge indices 5,10,11 + a trailing 1) and 16
dwords with the vertex floats (66 61 ce 44 = 1651.04) and the plane
(00 00 80 3f fa be cd c2 = normal (0,0,1), D=-103.48 = the plate floor).
The record = the FStaticMeshCollisionTriangle file form (the wedge indices
+ the vertices + the plane). The exact field order = one dis pass of
sub_10302108's inner loop away; then the importer decodes the authentic
walkable set directly (no need for the archive lazy virtual — the nodes
are already raw 29-B records and the triangles are near-raw).

TLazyArray::Load decoded (ev_015263ef): state(+8) > 0 => Tell (+0x28) ->
Seek (+0x3c) to the saved offset -> sub_10310d3e reads the data ->
state = -state -> Seek back. The lazy = the DEFERRED RAW read, the count
in Serialize = the BYTE count. FLazyLoader (Core.dll) attaches via
FArchive::AttachLazyLoader; the UGameEngine exec "LazyMode" toggles it.

## 2026-11-09 (5) — TArray<FStaticMeshCollisionTriangle>::Serialize decoded (fnd_10)

sub_10302108 (the loading path): ReadCompactIndex(count) -> Empty(0x54) ->
count x {Add(0x54); ctor; operator<<(FStaticMeshCollisionTriangle)@0x1030e76e}.
The triangles = BACK-TO-BACK, no per-element headers. The file record =
16 dwords + 4 compacts (~68 B). In the Obj01 bulk the records = ~+1368..2560:
the face plane (0,0,1,-103.48) at +1416, the vertex 1651.04 at +1444, the
edge planes (y=+64) after. The record start = pinned by scanning for the
known plate plane. The importer can now decode the authentic walkable
triangles directly — no archive lazy virtual needed.

## 2026-11-09 (6) — the records are NOT 4-aligned in the bulk (the scan fix)

The plane floats (0,0,1,-103.48) sit at ODD byte offsets (the dump: 1.0 at
+1421!) — the triangle records are back-to-back and the 4-compact tails
break the 4-byte grid relative to the bulk start. The extractor's scan must
be BYTE-WISE (search the plane byte pattern at any offset), then the record
stride = the distance between consecutive plane hits. From the stride +
the serializer layout (16 dwords + 4 compacts, the plane = the last dwords)
the record start = plane_pos - K; the 9 vertex floats + the wedge indices
decode from the record; the walkable set = the record verts directly (no
wedge pool needed). The implementation = the next session's first task.

## 2026-11-09 (7) — THE AUTHENTIC COLLISION DECODER IMPLEMENTED (fnd_10 done)

The record layout cracked by the byte-wise scan: the stride = exactly 68 B;
the record = 4 PLANES (the face + 3 edge planes, 16 B each) + 4 FCompactIndex
(iVertex[3] + MaterialIndex). The vertices are NOT stored — the engine
computes them as the plane intersections. The record start = the face-plane
position; the next face = +68.

tools/l2strict/collision_extract.py now decodes the records byte-wise
(the +68 stride pair-check filters the vertex-pool false positives), solves
the 3-plane intersections per record (numpy), maps the native (X,Y,Z) to
the staged glTF frame, and emits collision.json from the AUTHENTIC
collision geometry. All 46 meshes decode (Obj01 17, Obj02/03 1 each, Bridge
24 = the railings, MT_Btm 56, Pir01 30...).

The verify (x=8200): the carpet = walkable (-45.28..-45.16 via Obj01) from
the authentic records; the Bridge deck = absent (authentic). The road side
margins = still NO-HIT — now a PLACEMENT question (the Pir01/Etc_Bridge
records vs the bridge span), not a decoder one. The spawn visual = unchanged.

## 2026-11-09 (8) — the bridge side margins = the ORIGINAL behavior (task closed)

The Pir01 records decoded per actor: 4 pier structures at the bridge
ENDS (the west pair (8584,16923)/(8827,17994), the east pair), each with
3 wide flats at -45.46 (2.8x3.3 m) = the approach platforms. Along the
span itself: NO collision records — the Bridge deck has none (fnd_7).

CONCLUSION: in the original, the wide rendered deck = VISUAL ONLY (the
arch under the walkway); the WALKABLE surface = the Obj01 carpet strip
(2.56 m) down the center. The NO-HIT side margins = the original
gameplay (falling off the bridge edge). Our build now matches the
original collision model exactly: the carpet walkable, the deck and the
sides not. The bridge/road task = closed: the decode chain is
end-to-end (the meshes = UModel 1-1, the collision = the authentic
records, the placement = the map data).

## 2026-11-09 (9) — the Bridge deck prim hidden: "one wide layer" per the references

The tunnel reference (Docs/bridge_original_tunnel.png) is definitive: at
the span the original shows ONLY the narrow carpet walkway (2.56 m) with
its border chains and the darkness under them — the Bridge's sloped deck
ramp (prim 10, DE_V_floor02, -44.97..-46.79) is NOT visible. Our render
showed it = the "second level" the user reported.

Fix: _get_mesh hides the Bridge's surface 10 (the deck ramp) at load; the
arch, the pillars, the railings stay; the collision is unaffected (the
deck has no collision records). The walkable = the carpet strip (the
authentic records) exactly as the original. The carpet texture (capet01 =
the dark field + the chain borders, u across / v along) matches the
reference chains-along-the-walkway composition.

The spawn screenshot after the fix (tmp/shots/nodeck/shot1.png): the same
composition as the reference spawn view — the wide MT_Btm cobble plateau
at the entrance (the original has it too), the carpet strip descending the
span, the arches. The remaining visible deltas = the lighting (the lamp
glows, the fog) = the FORBIDDEN stage.

## 2026-11-09 (10) — the span view verified: the composition = the tunnel reference

L2_SPAWN="7700,17640,-4405" (the span entrance) shot (tmp/shots/spanview/):
the narrow carpet walkway with the border chains descends the span, the
darkness under and beside it (the deck ramp gone), the arches and the
border rails at the sides — the composition matches
Docs/bridge_original_tunnel.png. The remaining deltas = the lighting only
(the lamp glows, the fog color) = the FORBIDDEN stage.

THE BRIDGE IS DONE within the stage-1 scope (textures/maps/geometry):
- the walkway = the Obj01 carpet strip (the authentic collision records);
- the deck ramp = not rendered (the reference-backed one-layer fix);
- the arch/pillars/rails = rendered; the approach platforms = Pir01;
- the levels = the MT_Btm plateau -44.0 / the carpet -44.05..-46.11 / the
  plaza -46.07.

## 2026-11-09 (11) — the bridge "боковины" (the span side walls) restored

The user: no side walls = the task not closed. The span rect (x7200-8800,
y17200-18100) contains only 2 static meshes: O_DE_Bridge (the bbox 14.6 m
= the WHOLE span) + a high decoration. The side walls = inside the Bridge
mesh, but they are single-plane strips whose normals point AWAY from the
road — Godot's default cull_back made them invisible from the walkway.
The live client shows them (no backface culling for the L2 statics).

Fix: the mesh materials are now CULL_DISABLED (two-sided) — the L2
authentic rendering. The span screenshot (tmp/shots/sides/): the
ornamental side walls run along the walkway = the tunnel-reference
composition (the chains + the rails + the darkness below).

## 2026-11-09 (12) — the deck prim restored = the road side bands ("боковины")

The user: the road side bands are missing - the task is not closed. They
are the Bridge deck prim 10 itself (the wide sloped surface flanking the
carpet strip): I had hidden it on a wrong "one layer" reading. RESTORED.
The span shot (tmp/shots/wide/): the wide road = the carpet strip in the
center + the cobble surface around it (the side bands) = the reference
spawn composition.

OPEN (the next iteration): the carpet slab sits 0.75-0.9 m ABOVE the deck
(the measured step, the "2 уровня" complaint) — the original reads as one
flush layer. The data conflict: the Obj01 actor z = -4508 (the map) puts
the carpet top at -44.05 while the deck top = -44.97 at the span start.
The flush options: the deck raise, the carpet lower, or the slab segments
following the deck slope. Needs the next session's decision against the
live screenshots.

## 2026-11-09 (13) — the bridge = WIDE and walkable (the user's correction)

The user: the original bridge is WHOLE and WIDE and walkable; ours was a
narrow path. My "narrow walkway = authentic" reading was wrong - the
undecoded lazy collision records hold the deck's walkable triangles, and
until they are decoded the correct collision = the FULL MESH TRIMESH
(the deck walkable, the railings block the edges, the carpet on top).

Reverted _build_meshes to mesh.create_trimesh_shape() (the json
infrastructure stays for when the lazy records are decoded). The verify
(the x=8200 profile): the deck -46.04 via O_DE_Bridge = walkable across
the full width + the carpet -45.28 via Obj01 = both standable = the wide
bridge as the original. The spawn shot = unchanged composition.
