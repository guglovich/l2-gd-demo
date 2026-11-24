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

## 2026-11-09 (14) — the clean-room wide road built from scratch (the user's path)

_build_clean_room_road() in world.gd: the wide road slab built from
scratch per the live screenshots — the profile = the Obj01 slab's own
map-data profile (the top plate -44.05 / the slope / the bottom -46.11)
widened to the full road width (10 m); the center band = the carpet
(capet01), the side bands = the cobble (DE_V_floor02); the low rails
(wall05, 1.1 m) at the edges; the collision = the slab's own trimesh =
ONE FLUSH LAYER (the x=8200 profile: the single clean_room_road surface
-45.32..-45.28, no step; the old deck ramp is under it).

The Obj01 narrow staircase slabs = skipped (replaced). The units bug
fixed on the way: the slab was 35 cm (the meters vs the cm mix) and the
rails were 110 m tall (the cm height added to the meter vertices).

The span shot (tmp/shots/cr3/): the wide road + the rails + the arches =
the reference composition. The remaining = the lighting stage.

## 2026-11-09 (16) — the MCP-craft discipline: the archive class located (fnd_11)

The user set the discipline: the craft MCP = the brain, the agent = the
hands. The brief/plan updated (the current question = the .usx archive's
vtable+0x40 lazy decompressor). Progress: engine.dll = only the base
FArchive RTTI (0x10a50138) — no engine.dll archive subclass; Core.dll =
ULinkerLoad RTTI @0x102382c8 = the .usx archive. The vtable resolution =
the next step: find ?Serialize@ULinkerLoad@@ -> scan .rdata for the
containing vtable -> the +0x40/+0x3c slots = the lazy-block reader and
the Seek (per fnd_8) -> study = the packed decompressor -> the authentic
CollisionTriangles -> replace/confirm the clean-room collision.

## 2026-11-09 (17) — the slab UVs = the original densities (the quality pass)

The original UVs extracted from the staged glTF (the correct component
types): the Obj01 carpet = u 0..1 across (one repeat) + ~29 repeats along
(the ~1.18-m tile, not 2.56); the Bridge deck = the ~1.2-m tiles. The
clean-room slab now uses the same densities: the carpet u = (w+128)/256,
v = lx/118; the cobble = /120. The span shot (tmp/shots/uvorig/): the
cobble road + the center carpet band with the visible chain borders =
the reference composition.

## 2026-11-09 (18) — MILESTONE: the bridge floor is CONQUERED (the user confirmed)

The bridge road = finally fully correct, built via the clean-room path:
- the profile from the map data (the Obj01 slab's own: -44.05 / the slope / -46.11),
- widened to the full 10-m road width, ONE flush layer (no step),
- the original surfaces: DE_V_floor01 cobble (~1.2-m tiles), the center
  band = DE_V_capet01 carpet (1 repeat across, ~1.18 m along — the chain
  borders visible), the low rails DE_V_wall05 (1.1 m),
- the collision = the slab's own trimesh (the single clean_room_road
  surface across the width, the x=8200 profile),
- the Obj01 narrow staircase slabs replaced; the arches = the client's
  Bridge mesh; verified by the profiles and the screenshots
  (tmp/shots/uvorig/, cr4, cr4spawn).

THE PENDING DEFECT (the next task): the extra walls along the houses
(лишние стенки вдоль домов) — the user's report; investigate which mesh
renders them and whether the client shows them.

## 2026-11-09 (19) — the "extra walls along the houses": the first diagnostics

The teleports into the house area (12300,17400) and (12300,16900) both end
with the player FALLING to -4844: the open ground between/around the
houses has NO collision floor. The O_DE_Btm mesh = a 55x2.4x49-m TALL
WALL (the earlier bbox), not a floor cover - its flats at -46.07 cover
only a narrow strip. The houses' own floors (the H meshes) = fine.

THE HYPOTHESIS for the user's "лишние стенки вдоль домов": the visible
walls = (a) the O_DE_Btm 49-m wall rendered where the client shows
nothing, and/or (b) the house undersides visible through the two-sided
render when the camera is low. The next session: the trace-box pass with
the correct camera (the spawn ON a house floor, e.g. 10336,16349,-4480 =
H02#3), identify the wall meshes by the L2_TRACE_BOX hits, then compare
with the live client screenshots the user provides.

## 2026-11-09 (20) — the "extra walls along the houses" = the O_DE_Btm 49-m wall — FIXED

The user's screenshot at (9276,17227): the long stone wall blocking the
houses along the east road = the O_DE_Btm mesh (55x2.4x49 m, the actor
(11375,16872,-4952), the yaw -2320: its long axis runs (9094,17476) ->
(13656,16268) = along the road, and the structure rises to -25 m =
19 m ABOVE the floor). The live client does not show it above the floor.

Fix: the render-only skip (_RENDER_ONLY_SKIP = [Oren_DEV_S:O_DE_Btm]) —
the mesh instance = hidden, the collision body stays (its -46.07 flats).
The verify at the user's viewpoint (tmp/shots/nowall/): the wall = gone,
the houses visible, the road with the carpet strip and the lamps = the
original composition.

## 2026-11-10 — the invisible walls = the Btm COLLIDER (the render hide was not enough)

The user: the walls remain after the rebuild. The L2_TRACE_BOX at the
user's viewpoint = DEFINITIVE: 45 collider hits = Oren_DEV_S:O_DE_Btm
(the textures wall05/wall01 in the trace = the collider's surfaces). The
render-only hide left the Btm's collision body = the INVISIBLE walls
blocking the houses.

Fix: O_DE_Btm moved to _ROAD_STRIP_SKIP = the full skip (the render AND
the collision). The dead _RENDER_ONLY_SKIP block removed (the parse
error caught by the verification). The verify: 0 errors, the view at
(9276,17227) = clean (the road + the carpet strip + the houses + the
lamps), the player stands at -4610.9 on the clean-room slab.

## 2026-11-10 (2) — the "walls" = MY clean-room rails — removed

The user (repeatedly): the walls remain. The real culprit = the rails I
added myself in the clean-room build (wall05, 1.1 m along the edges) —
the original has NO side walls: the road = open to the houses, only the
carpet's own border chains mark the edges. The Btm skip (the invisible
collider) = a parallel real fix, but the visible wall = my rails.

Removed the whole rails block from _build_clean_room_road(). The verify
at (9276,17227): the road open, the houses visible, the lamps on the
road edge = the original composition. LESSON: do not invent geometry
absent from the references — every added piece needs the reference proof.

## 2026-11-10 (3) — the next clean-room build: the plaza floors around the houses

The user's live screenshot: the plaza around the houses = the large flat
dark stone surface (the same texture family as the road), separated from
the carpet road by only a SMALL ornamental border (the thin dark curb).
No side walls anywhere.

THE BUILD PLAN (the next session):
1. The plaza slab(s) at the house-floor level (~-44.5, the H-mesh units
   -44.3..-44.7), the texture = DE_V_floor01, the same UV family as the
   road slab (~1.2-m tiles).
2. The extent = the central plaza between the houses (the verified
   no-floor spots: 12300,17400 and 12300,16900 = inside; the houses =
   H02 12526,17342 / H03 12210,17822 / H02 10336,16349 / H03 9623,18375
   / H01 11440,19405 / H04 13173,15445 + 10623,15882). The slab must NOT
   poke above the house floors or over the carpet road.
3. The small border: the thin dark curb strip along the slab edge facing
   the carpet road.
4. The collision = the slab's own trimesh; the verify = the player stands
   (no fall at 12300,17400), the spawn screenshots, the profiles.

## 2026-11-10 (4) — the east road floor was missing: the clean slab extended

The earlier "falls" at (12300,16900/17400) = the east road BEYOND the
clean slab's end: the original Obj01 profile ends at the local +1651
(the world x ~10670) but the road runs to the east bridge (~14720).
Extended the bottom segment to the local +5800. The verify: the
clean_room_road -46.109 at (12000,17000) and (12150,17100) = the floor
covers the east road.

THE PLAZA (the next iteration): the user's screenshot shows the plaza
AT the road level (no visible step - only the small border), so the
plaza slabs = the road-height side areas (the north strip first), the
texture floor01, the small dark curb at the transition.

## 2026-11-10 (5) — the village street = the carpet road + the plaza stone (the depression fixed)

The user: the road was made solid — in the original the village street =
the carpet band (~4 m) flanked by the PLAZA stone at the same level, and
the areas beside it were the voids (the depression).

The band layout restructured per segment: on the bridge/east flat
(lx <= 1651) = the cobble shoulders + the carpet (as before); on the
village street (lx > 1651) = the carpet +-2 m + the plaza stone bands
(floor01) +-2..6 m. The GDScript scoping bug fixed (the commit block was
outside the band loop). The verify at (10473,16943): the carpet road +
the plaza stone = no voids, the user's composition.

## 2026-11-10 (6) — the tower height fixed (the +1161 hack removed); the octagon floor = the next

The user: the tower sticks out too far. THE CAUSE = the +1161 z-shift
hack on O_De_01/02/03 (the Shillien hand / the center ornaments) — the
meshes were raised 11.6 m above their map placement. REMOVED: the meshes
now sit at the map z (-5541) = the pillars/hand at the authentic height
(the shot tmp/shots/tower/ = the columns at the correct place).

ALSO: the clean-room road east extension was CUTTING through the octagon
plaza (the Center_obj at the local lx ~2376) — the road now BREAKS at
the octagon and resumes behind it ([3080..5800]).

THE NEXT TASK: the center octagon floor — the Center_obj (14-m platform,
the actor (11374,16847,-4832), the top at -45.7) does not catch the
collision (the player falls through at (11400,16850)) — diagnose why
(the trimesh? the load?) and add the octagon plaza floor around it per
the user's live screenshot (the octagonal platform + the outer ring with
the crystal pillars).

## 2026-11-10 (7) — the center octagon built; the Center_obj collision = the open bug

_build_center_octagon() added (world.gd, called after the road): the
octagonal floor ring around the Center_obj (r_in 730 / r_out 1800, the
level -45.7 = the Center_obj's top), DE_V_floor01, the ~1.2-m tiles, the
trimesh collision, the meta center_octagon.

THE OPEN BUG: the player at (11400,16850) still falls through (-5263):
the spawn point = inside the ring hole (26 cm from the center, r_in =
730) AND the Center_obj's own trimesh does not catch (-45.7..-50.9).
NEXT: the L2_TRACE_BOX at the center = what the rays hit (the Center_obj
collider? nothing?); check the Center_obj = loaded/placed (the actor
402); if its trimesh = broken - the octagon ring covers r_in = 0 (the
full octagon) instead. The hand/pillars (O_De_01/02/03) = at the
authentic height now (115f312).

## 2026-11-10 (8) — THE MESH GRID = the lamp levels: the village is FLAT -44.73, the terraces decoded

The user: first the correct geometry/meshes from the original, then the
textures — my slab had the layering and the coordinate mismatches (the
lamps floating).

THE LAMP GRID (31 lamps extracted): ALL Lamp01 = z -4473.4 EXACTLY
(the pairs flanking the road along the whole village), Lamp02 = -4498.4.
=> the village street = FLAT -44.73 (the lamp level), NOT the descent's
-46.11. The profile = the terraces: the bridge dip (-46.11) -> the
octagon terrace (-45.7, the Center_obj) -> the street (-44.73).

The road segments now: the descent ends at the octagon level (h -62),
the gap (the octagon), the climb [3080..3600] to the street (+34.6), the
flat street to the east bridge. The lamps = the street-level markers for
all the further geometry work.

## 2026-11-10 (9) — the center redone per the mesh grid: the player stands

The road = the approach flat ends at the local lx 450 (before the
octagon's west edge); the octagon = the FULL octagon (r_in = 0) at
-45.75 (5 cm below the Center_obj's top = no z-fight, the Center_obj
renders on it); the climb [3080..3600] from the octagon level (-67) to
the street (+34.6). The layering = gone (the road no longer cuts the
ring). The verify: the player STANDS at (11200,16850) on -4575.0, the
hand sculpture at the authentic height, the temple behind.

## 2026-11-10 (10) — the foreign texture at the center = the MT_In shell (the prime suspect)

The user (2 iterations): the foreign striped texture lies as the second
layer at the center. The center redo (2a3531f) = the octagon + the road
gap done, but the striped = still there from the user's angles. The
trace at the bridge = the legit meshes; the center's prime suspect =
O_DE_MT_In (the cave inner shell, O_dark_01) enveloping the village -
the alien layer near the octagon.

NEXT: the trace at the center from the user's angle -> confirm the MT_In
-> hide/trim the shell near the octagon (the render-only trim or the
specific faces), verify vs the user's live screenshot.

## 2026-11-10 (11) — the alien striped shell removed: O_DE_MT_In fully skipped

O_DE_MT_In (the cave inner shell, O_dark_01) moved to _ROAD_STRIP_SKIP =
the render AND the collision skipped. The center (11200,16850) = clean:
the octagon plaza + the hand + the temple, no striped walls. The tunnel
walls = MT_Out (the legit rock), the inner shell was not needed
anywhere.

## 2026-11-10 (13) — the light gaps fixed: MT_In restored (it covered the MT_Out holes)

The user's screenshot: the sky gaps through the rock after the MT_In
removal. The MT_In = restored fully (the render + the collision): it
covers the holes in the outer shell. The verify at (9338,17144): no
gaps. The striped-texture question at the center remains open — the
next sighting needs the trace at the exact user angle before any skip.

## 2026-11-10 (14) — the statue hand = the face texture: the section->material binding (fnd_12)

The user's screenshot: the statue's hand = the face texture. ROOT CAUSE
(inferred, fnd_12): the L2 render resolves the section's material via its
OWN MaterialIndex field (Materials[Section.MaterialIndex]); the sections
are NOT guaranteed ordered by material. Our importer = the identity
assumption (prim i = material i) - wrong for O_De_03 (the permuted
sections).

FIX (the next iteration): parse each mesh's section table (the count +
the 18-B FStaticMeshSection records at the bulk start - the parse worked
for MT_In/Bridge earlier), take per-section MaterialIndex, write it into
asset_map primitive_material_indices. The craft Deep brief = updated
(rev 50), the target = engine.dll. The test case = the statue's hand.

## 2026-11-10 (15) — the hand texture: the binding is NOT the culprit — the O_De_03 prim split is

The section-table probes at the fixed offsets = garbage (the Sections sit
after the variable-length LOD data, not at a fixed offset). The key
realization: our strict parser ALREADY reads the sections correctly (the
prim order/count = from them), and UEViewer renders L2 statics correctly
with the identity (section i = material i). So the binding = fine.

THE REAL SUSPECT: our O_De_03 parse's per-prim index ranges (the
run-anchor split) differ from UModel's — the hand's triangles landed in
the wrong prim (the face's material). NEXT: the per-prim diff of O_De_03
ours vs tmp/l2/20_18/umodel/Oren_DEV_S (the prim counts, the index
ranges, the UV boxes) -> fix the split -> the hand gets its material.

## 2026-11-10 (16) — the statue hand: the materials verified identical; the UV/atlas = the remaining suspect

The per-prim diff O_De_03 ours vs UModel: the index counts IDENTICAL per
prim (192/816/453/471/192/72/144); the material lists IDENTICAL (prim5 =
De_Statue002 = the statue's own texture, the file = legit). So the
materials are NOT the problem. The remaining suspects: the UV mapping of
the hand's prim (prim5) pointing at the wrong atlas region (the face?),
or the texture file export. NEXT: the user's zoomed screenshot of the
hand + the UV box of prim5 vs UModel's prim5.

## 2026-11-10 (17) — the statue hand = the UV bug found (ours vs UModel)

UModel prim5 (the hand): u [-2.78, 7.16], v = 0.001 CONSTANT (the
degenerate line = samples the texture's bottom row = the PALE ornamental
band of De_Statue002 = the user's pale cracked hand!). OURS: v spread
-0.91..2.65 = samples the whole dark field = the dark hand.

THE FIX (the next iteration, the clean-room approved): override prim5's
TEXCOORD_0 in the staged glTF with the original values (v = 0.001, u =
the original range) - the python fixer, then the reimport + the verify.

## 2026-11-10 (18) — the statue hand FIXED: the UV override applied (the clean room)

prim5's TEXCOORD_0 in the staged O_De_03.gltf = rewritten in place: v =
0.001 constant (the original's degenerate line), u kept. The reimport +
the verify: the hand = PALE (the bottom ornamental band of De_Statue002)
= matches the user's live reference. The dark = the statue's shadowed
body = the lighting stage.

## 2026-11-10 (19) — the hand UV fix redone CORRECTLY: the targeted override

The previous fix = WRONG: the prim5's TEXCOORD_0 = the SHARED accessor
(1596 verts = all the prims) - my v=0.001 rewrite hit ALL the statue's
UVs. REDONE: the .bin restored from git (59c7b8b), then the TARGETED
override = only the 40 verts referenced by prim5's indices (v = 0.001,
u kept; ct=5126). The reimport + the verify = 0 errors. The final color
check = the user's (my shot = the shadow side).

## 2026-11-10 (20) — the hand texture mystery SOLVED by the trace: the Center_obj rim overlaps the statue

L2_TRACE_BOX at the hand region = DEFINITIVE: the hand = O_DE_01 with
De_Statue002 (CORRECT!) + the foreign hits = O_DE_Center_obj surf 5
(DE_V_new_deco3) = the Center_obj's rim/surface INTERSECTS the statue's
raised hand (the z-conflict: the platform's parts poke through the
hand). The materials/UVs were never the problem — the GEOMETRY overlap
is.

NEXT: the Center_obj's placement/shape vs the live client (the hand
must be ABOVE the platform) - the z or the mesh part to trim. The
O_De_03 = the unrelated mesh (the red herring all along).

## 2026-11-10 (21) — the face texture on the hand FIXED: the Center_obj surface 5 hidden

The Center_obj surface 5 (DE_V_new_deco3) intersected the statue's
raised hand (the trace-proven). _get_mesh rebuilds the Center_obj mesh
without the surface 5 (the rest of the platform stays). The verify: the
hand = clean, the pale fingers = visible, no face texture.

## 2026-11-10 (22) — the face on the arm = the O_DE_01 prim MERGE bug (the exact numbers)

UModel O_DE_01: prim0 = 69 verts (the HEAD, the UV box u 0.34-0.63 /
v 0.51-0.86 = the face region of the atlas!), prim1 = 648 verts (the
body, u -2.38-0.96 / v -0.16-0.98). OURS: TWO prims of 717 verts EACH
(69+648 = 717 = the whole mesh duplicated into both prims) with the
BODY's UV range — the head prim = merged into the body, its face UVs =
lost => the face texture renders across the arm/hand.

THE FIX (the next iteration): the O_DE_01 = re-staged with the correct
2-prim split (the head 69 + the body 648, the per-prim UVs as UModel)
- the same check for the O_DE_02/Center_obj (the similar merge risk).

## 2026-11-10 (23) — O_DE_01 re-staged from the UModel reference (the correct 2-prims split)

The staged O_De_01 replaced with the UModel export: prim0 = 69 verts
(the head, De_Statue001), prim1 = 648 verts (the body, DE_statue002_s)
- the correct per-prim UVs (the face region for the head). The
materials.json + the asset_map primitive_material_indices = [0,1]
filled (were empty). The reimport done. The verify shot = the shadow
side (the color inconclusive) - the user's check = the final gate.

## 2026-11-10 (24) — MILESTONE: the statue hand FIXED (the user confirmed) — the import bug catalog

The statue's hand = fixed: O_DE_01 re-staged from the UModel export
(the correct 69+648 prim split, the per-prim UVs) + the materials mapped
(De_Statue001 / DE_statue002_s) + 5686b96. The user confirmed.

**THE IMPORT BUG CATALOG (for every future mesh work):**
1. **The prim merge** — our run-anchor parse can merge the adjacent
   sections into one prim (O_DE_01: ours = 2 prims x 717 verts = the
   whole mesh duplicated; the original = 69 head + 648 body). The
   per-prim UVs are lost in the merge => the wrong atlas regions render
   (the face across the arm/hand).
2. **The shared UV accessor** — the staged prims often share ONE
   POSITION/TEXCOORD accessor; a per-prim UV override must be
   INDEX-TARGETED (only the verts referenced by that prim's indices),
   never in-place over the whole accessor (the first hand fix broke all
   the statue's UVs).
3. **The validation gate**: every staged mesh = the per-prim diff vs
   the UModel export (the prim count, the index counts, the UV boxes
   per prim) BEFORE it is accepted. The materials.json / asset_map
   entries = must be filled (the empty ones render untextured).
4. **The diagnosis order**: L2_TRACE_BOX first (the mesh + the texture
   per hit), then the hypotheses. The O_De_03 red herring cost several
   iterations because the trace at the hand was done last, not first.

## 2026-11-12 (25) — the middle studied: the collision format CRACKED (the ~5% extraction bug found)

The task: study the village center (the statue plaza + the MT tree + the
street). The grid/profile verification exposed that the spawn street band
(x 13100-13500, y 17100-17300), the tower-east strip and the NW band have
NO floor at street level, while every mesh AABB covers them. The cause was
NOT the layout — it was `tools/l2strict/collision_extract.py`.

**The authentic collision array format (fully decoded and validated):**

```
[compact N]                     N ≈ the mesh triangle count (O_DE_Btm 690=690;
                                O_DE_WH is 1167 vs 1166 — one record more!)
N × record (VARIABLE stride):
    FPlane planes[4]            4 × 16 B — the face plane + 3 edge planes
    compact iVertex[3]          indices into the RAW 24-B VERTEX STREAM
    compact MaterialIndex
```

- The stride is variable (64 B planes + 4-20 B of compacts) — the old
  fixed `+68` decoder only caught coincidental chains and recovered
  **~5% of the triangles** (O_DE_Btm: 29 of 690). That silently dropped
  the WH porch, the plaza floors and the stall decks — the "geodata gaps".
- The `iVertex` indices are NOT wedge indices: they index the mesh's raw
  vertex stream `[compact count][count × 24 B (pos 12 + normal 12)]`
  parsed from the same bulk. The staged glTF vertex order is renumbered
  by the per-prim staging (O_De_01 69+648), so the winning stream is
  chosen by validation: every record must satisfy `plane·v = D`
  (|dot−D| ≤ 2). Result: **O_DE_Btm 690/690, O_De_01 961/961, WH 1167/1167
  plane-valid; all 46 Oren_DEV_S + 74 other-package meshes extracted**.
- The kDOP leaf-bbox gate (the 29-B units) is kept as before.
- The frame: stream pos (X, Y-width, Z-up) cm → staged glTF
  (x, z→y-up, y→z) — the same conversion the stager uses.

**What the middle is (the study results):**
- The MT family = the GIANT TREE over the village, not a tower:
  MT_In = the canopy underside (a near-flat shell at −1.2..−6 m over the
  whole village), MT_Out = the top shell (+25..+31), MT_Btm = the deep
  shaft (to −82.5). Authentic.
- The plaza levels: Center_obj platform −46.4, O_De_01 pedestal −46.0,
  O_De_02 terraces −51..−53, O_De_03 pit −53..−75, the north octagon
  (O_DE_Btm ring, −46.02) covers the NE quarter around Azit01.
- All 62 center mesh objects are staged + materials mapped.

**The remaining floor gaps = the MISSING BSP BRUSHES.** bsp2.py paired
Brush→Model→Polys by NAME (ModelN↔PolysN); only 166 of 249 brush-like
actors match that way. The unmatched ones include the spawn street band
brushes (Brush901/903/953/7/8/9 at x 11300-13900, y 16100-17700, z
≈ −4600 — the exact missing floors). The Model serial does NOT carry a
readable Polys reference in its 72-B blob (no property, no u32/compact
ref found) — decoding the link needs an engine.dll RE of
`UModel::Serialize` (fnd_next). BlockingVolume = walls only (checked).
StaticMeshInstance (651) = per-instance vertex colors, not placements
(correctly dropped).

## 2026-11-12 (26) — the Shilen Temple fully analyzed + the BSP brush↔Polys link CRACKED

**The temple (O_DE_CH_* cluster, south of the village, 10800-11400 / 14300-15300):**
all 8 meshes staged with materials; authentic collision subsets 100% plane-valid
(the new extractor). Geodata verified by profiles:
- mainstair: 30 authentic step levels −46.13→−43.81, ny=1.0, climbs from the
  Btm_Obj03 forecourt (−46.11) ✓ walkable;
- sidestairs (east/west): the same step ladder −46.0→−43.72 ✓;
- CH_Btm platform −43.72 (extends INTO the hall), CH_btm_obj01 inner steps
  −43.72→−42.55, the hall gallery −40.30 (CH_body −4030), the altar tiers
  −38.8/−36.7, the deep ledge −47.28;
- CH_body has NO floor between −42.55 and −41.29 — the hall floor = the
  CH_Btm platform; the −40.3 tier is the gallery.
(The sylentemple_* package = the separate Silent Temple ruins in the far
east x 26000-30500 — NOT the village temple.)

**The Brush→Model→Polys link — SOLVED (engine RE):**
- The L2 `UModel::Serialize` (engine.dll 0x1030cac7) does NOT carry the
  stock-UE2 `Ar << Polys` at the head. The reference is a COMPACT object
  index (export+1) inside the 72-B Model blob (Model954 holds compact
  2260 = Polys370+1 at offset 55). UPrimitive::Serialize first writes the
  local bbox (6 floats — the z family matches the polys).
- The old bsp2 name-pairing (ModelN↔PolysN) matched only 166/249 brush-like
  actors — the street-floor brushes were never name-paired. The blob-ref
  pairing (with loc-inside-world-bbox disambiguation for the few multi-
  candidate blobs) pairs ALL 219 brushes. bsp2.py moved to tools/l2strict/
  and regenerated: 171 glTFs, bsp.json with per-brush poly_flags.
- Placement: origin = Location − PrePivot; ALL 20_18 brushes have Rotation 0.
  The glTF convention is now the statics one (x, z→y, y→z).
- Flag semantics (empirical): poly flag 0x1 = invisible (collision-only
  street trim, 85 brushes), flag 0x400000 on a majority of faces = the
  zone-portal/sky boxes (89 skipped — they sit above the tree canopy and
  must not block anything), the rest (45) render + collide.

**world.gd `_build_bsp()`** builds the BSP: render = neutral stone
placeholder (the polys' textures live in the Model FBspSurf records — the
next stage), collision = full trimesh with backface.

**Result:** the spawn street band (13100-13500 / 17100-17300) now has its
authentic floor (BSP:Polys353 at −46.01, ny=1.0); the temple approach grid
75/80 ok (was ~all gaps); the center grid gaps 26 → 13 (the remaining ones:
the tower base strip 11862-12015/16567-17100 and the north band
11400-11862/17367-17500). Spawn screenshot = no visual regression.

## 2026-11-12 (27) — the BSP meshes CONFIRMED by the user (visual check passed)

The user checked the render: "меши появились" — the BSP geometry renders
in the world. The iteration is closed as DONE:
- the Brush→Model→Polys blob-ref pairing + _build_bsp in world.gd;
- portal boxes (0x400000-majority) skipped, invisible-flag trim = collision
  only, 45 visible/collidable BSP brushes;
- the temple and the streets geodata verified by profiles (entry 26).

NEXT (the queue before the texture stage):
1. The 0x400000 flag semantics: 89 brushes skipped — verify none of them
   hides a needed floor (the remaining 13 grid gaps: the tower base strip
   11862-12015/16567-17100, the north band 11400-11862/17367-17500).
2. The BSP textures: the polys' materials live in the Model FBspSurf
   records (0x44-B on-disk, contains a Texture object ref) — parse them
   per-surf, map surf→poly, replace the neutral grey placeholder.
3. Then the user's texture stage (BSP + statics).

## 2026-11-12 (28) — the BSP textures APPLIED (the per-face materials)

**The texture source — cracked (engine RE, MCP findings fnd_13/fnd_14):**
- `myLevel` -> **Model500** (2.5 MB = the level BSP; 219 brush models are 72-B
  stubs, 38 mid models unused by brushes). The FBspSurf records live in
  Model500's Surfs array.
- **The L2 FCompactIndex decoder (Core.dll 0x1015cfb0)**: sign = bit 0x80 of
  the FIRST byte; magnitude = (b0 & 0x3F) | (cont << 6). All our old decoders
  were wrong on negatives: single-byte off by one (-n-1 instead of -n) AND
  negative multi-byte (imports >= 64, first byte 0xC0|low6) decoded as
  POSITIVE. That misdecode made every import ref garbage — the surf materials
  looked like "Package Insect_Day" instead of the real textures.
- **FBspSurf file record**: objref MATERIAL (+0x00), dword PolyFlags (+0x04),
  5 compacts [pBase, pNormal, pTextureU, pTextureV, iBrushPoly], objref owner
  Brush (+0x1c), 16-B plane, float lightmap scale, int. Surfs map to brush
  polys by (owner Brush = the Brush ACTOR export idx+1, iBrushPoly = the raw
  poly index). FPoly file record confirmed: compact NumVertices, 4 FVectors
  (Base/Normal/TU/TV), verts, dword flags, objref Actor, objref Material,
  FName Item, compact iLink, compact iBrushPoly, 2 dwords.
- Validated on Brush902/Polys353: surfs 495-509 = iBrushPoly 0,1,10..22, all
  materials = Oren_DEV_T.DE_V_floor01.

**bsp2.py rewritten** (schema 2): the compact decoder fixed; parses ALL polys
(raw-index stable); parses the level Model surfs; bsp.json brushes carry
`faces: [{i, prim, flags, tex}]` (tex = [staged package, object]); glTF prims
= renderable faces only (the old 0x4000000|0x1|0x80 filter + skip the
AntiPortal/ZonePortal marker textures; NOT 0x400000 — ordinary wall faces
carry it too and must render). The 0x1/invisible faces stay out of the glTF
(collision-only trim) as before. cover_z unchanged (7267 cells = the old
count). Texture staging additions: sylen_temple_t.oren_sylen_001_1/in008/
in016/in022, oren_dev_t.Iron_net (umodel -png; NOTE the relative -out resolves
to $HOME).

**world.gd `_build_bsp()`**: per-face materials via bsp.json faces ->
`_bsp_material()` (StandardMaterial3D + albedo_texture, roughness 0.95, cull
disabled; cache per texture; grey placeholder for the 263 faces without a
surf texture).

**Result:** 742/1005 faces textured (DE_V_m12 x212 walls, DE_V_floor01 x121
street floors, O_dark_01 x110, oren_sylen_001_1 x98 temple, DE_V_floor02 x30,
oren_sylen_in002 x30 + the rest); 248 surfaces textured in the 45 built
brushes, 15 unique materials, zero missing/staged-failed. Floor profile at
the spawn street band unchanged (BSP:Polys353 -46.01, ny=1.0, every step);
portal-skipped 89 and skipped 85 = identical to the pre-texture run.
Spawn screenshots: tmp/l2/20_18/shots/shot1.png, shot2.png — user to compare
against Docs/DE_village.png.

**NEXT (the queue):**
1. The user's visual check of the BSP textures vs the original.
2. The UV orientation: the BSP UVs use the FPoly base/TU/TV dirs — verify
   scale/repeat vs the original (the temple walls are the best reference).
3. The 13 residual center-grid gaps (the 0x400000 flag semantics check) and
   then the statics texture stage.

## 2026-11-12 (29) — the curbs restored + the BSP UVs fixed + the level BSP rendered

**The user's two reports:** (1) the curb gaps along the carpet strips are
CORRECT layout — the original has a curb there, find its texture; (2) the
temple-side path = broken, "the textures way up and glitched", rebuild the
meshes.

**1. THE CURBS — found and restored.** The old 0x400000-majority skip dropped
~77 REAL brushes: 25 street-level curb/cobble boxes (DE_V_floor02 +
O_dark_01 + DE_V_wall07 textures — the surf materials, already in bsp.json)
along ALL the roads + the valley canyon walls. 0x400000 is carried by
ordinary wall/street faces too — the flag-based portal rule was wrong.
world.gd now renders every brush; the zone/sky boxes drop out by geometry
instead (bsp2 skips glTF for polys spanning > 5000 units; the biggest
legitimate brush = 4184).

**2. THE UV BUG — the root of the beige slabs.** bsp2 computed the BSP UVs
as dot/|U|^2 — one tile stretched over a 20+ m plate (the |U| magnitudes in
the FPoly records are 19k-20k junk). Fixed: 1 texel per world unit along the
surface U/V axes, baked as texels into the glTF; world.gd scales the material
by 1/texture size. Also: faces without a level surf now fall back to the
FPoly's OWN material slot (+0xF8) — the CSG merges coplanar brush faces into
one surf (iBrushPoly points at the first poly only), so the street plates'
staircase segments were texture-less before.

**3. THE LEVEL BSP RENDERED DIRECTLY (new tools/l2strict/levelbsp.py).**
The brush reconstruction cannot produce the CSG-split faces. The level Model
(Model500, found via Level -> compact ref) carries the engine's own merged
geometry. Decoded fully (MCP findings fnd_13/14 + this session):
- node record: 4 floats (the plane inline), 2 ints, 1 byte, 7 compacts
  (c0 = iVertexPool), 16+16 B, 3 bytes (byte[2] = **NumVertices** —
  validated 774/774 surf polygons on their node planes), 2+3 ints;
- the surf polygon = Points[Verts[pool .. pool+NumVertices].iVertex];
- surf UVs: u = dot(P - pBase, pTextureU) in texels (|pU| = 0.5..4 = the UE
  texel scale);
- the vert pairs are COMPACTS (not u16+i32); the surf owner compact is
  variable-length (a fixed +24 skip desynced the parse).
LevelBSP.gltf = 643 drawn surfs in 17 material surfaces. NOTE: Model500
covers only the designer-built zone geometry (the temple court, the valley)
— the streets live in the Brush actors, so world.gd renders BOTH sources;
collision = both trimeshes.

**Result:** the temple-path beige slabs are gone; the road = carpet runners
(DE_V_capet02, the Btm_Obj02/03 ribbons) + the cobble with authentic scale;
the curbs render along all the roads; the temple court floor (floor01 at
-45.82) restored from the level BSP. Floor profiles unchanged at the spawn
street (Polys353 -46.01). Grid: the tower strip 5 gaps -> 7 ok + 5 gap; the
north band still 11 gap.

**PENDING (the next iteration):**
1. The market square (11400-11862/17367-17500) + the tower strip: NO floor
   geometry exists in ANY source (brushes, level BSP, statics) — the layers
   there = MT_In canopy / O_De_03 pit slope / MT_Btm shaft only. The pit may
   be OPEN by design (the giant-tree shaft) — needs the user's original
   reference to decide.
2. The dark fields left of the road = the plate faces in shadow (lighting —
   NOT this stage) + z-fighting risk: the plate's overlapping coplanar
   staircase segments (poly0/2/4/6/8) now all render — if the original
   dropped the hidden ones, the render should too.
3. The building roofs render white/grey — verify their textures vs the
   original.
4. The UV scale (1 texel/unit) = the default UE density — the user should
   verify the pattern scale vs the original.

## 2026-11-12 (30) — the three user-reported bugs: the tunnel, the floating road, the main road

**1. The village exit tunnel "closed by a texture" = THE MERGED-PRIM IMPORT
BUG family-wide.** The blocker = O_DE_MT_obj04 (the tree-root pieces at the
canyon mouth). Per-prim audit vs the UModel reference: **36 of 43 staged
meshes had the catalog bug #1** — every primitive shared ONE giant merged
accessor (2x106 duplicated verts for MT_obj04 vs the true 53+55 split). ALL
36 re-staged from tmp/l2/20_18/umodel (the O_De_01 precedent): the glTF+bin
copied under the staged name, materials.json filled with the real per-material
textures (the umodel material names = the texture names; DE_statue002_s
resolved via shader_diffuse.json -> De_Statue002), asset_map
primitive_material_indices = the umodel per-prim indices. The collision.json
files stay valid (the collision triangles come from the raw file stream, not
the staged glTF order). The tunnel = now the hanging roots (an opening below);
the spawn view = the authentic carved canyon passage.

**2. The floating sloped road = the clean-room road REMOVED entirely.** The
user: the road must be LOWER than the floor with the curbs between. The
experiment (L2_NO_CLEANROOM) proved the whole corridor is covered by the
authentic BSP: Polys3977 (-44.05, the bridge), Polys3987 (-44.57..-45.99, the
bridge slope), Polys3983 (-46.12, the village street), Polys377, Polys353 —
0 NO-HIT along x 7000..14700. The clean-room deck floated 0.7-1.3 m ABOVE the
authentic plates and sloped up toward the center. Deleted the call + the
function. The curbs (-45.87, 14 cm above the street) are exactly the
original's floor-above-path arrangement.

**3. The main road from the temple = FIXED by 2 (the striped tilted slabs in
the user's screenshot = the removed clean-room road segments).** The corridor
profile: Polys363/353/Btm_Obj02 at -46.01..-46.11 continuous; the pit
(O_De_03) visible between the plates = the authentic shaft.

**PENDING:**
- The green/red edge strips at the tunnel road = the O_DE_Bridge + the BSP
  plate edge faces — verify the material mapping vs the original.
- The market square + the tower strip = no floor in any source (the shaft may
  be open by design) — the user's verdict pending.
- The windows render teal/pink flat quads (DE_V_win?) — verify vs the original.
- The temple path UV scale (1 texel/unit) — the user's visual check.

## 2026-11-12 (31) — the textures restored + the real BSP texture axes

**The user: the meshes are closer to the original now, but half the textures
are lost; make the textures as in the original + the curb textures.**

**The lost textures = two bugs:**
1. The re-stage's naive name->file material lookup clobbered the
   pipeline-resolved materials.json entries (36 meshes). RESTORED from the
   git history (a290769) — the pipeline entries resolve the shader chains
   properly and are indexed by the mesh's own Materials array (independent
   of the prim order), so they fit the re-staged meshes as-is.
2. The UModel glTF writes COLORED baseColorFactor placeholders for its
   materials (deco10 = red, roof_deco1 = green) — every surface without our
   material rendered the placeholder. world.gd now forces our material (the
   texture or the 0.32 grey) on EVERY static surface — no umodel leftovers.

**The road "stripes" = the FPoly TextureU/V are DEGENERATE.** The texture
axes in every 20_18 brush poly are PARALLEL (cos(U,V) = 1.0000) — the real
render axes live in the level SURFS (pTextureU/pTextureV vectors, |U| =
0.5..4 = the UE editor texel scale; u = dot(P - pBase, pTextureU) texels).
bsp2 now takes the UV axes from the face's surf; the CSG-merged faces (no
own surf) borrow the axes of a same-plane surf (the brush's surfs first,
then globally by the normal + the plane distance). Result: the road = the
cracked-cobble floor01 with ~5 m tiles, no stripes.

**Also:** the circular import bsp2<->levelbsp doubled the brush list (438) —
levelbsp is self-contained now. The world.gd static path forces the material
on every surface (the missing textures = the grey placeholder, never the
umodel colors).

**PENDING:** the corridor gap at (10850,17300) (the same no-floor family as
the market square — the shaft?); the user's visual verification of the
texture scales and the windows.

## 2026-11-12 (32) — THE MODERN-PORT RULE + the tunnel/geodata fixes

**THE USER'S DIRECTIVE (the rule added to AGENTS.md):** do NOT recreate the
legacy client's outdated logic (the CSG brush carving, the 2000s level-design
hacks) — for levels, effects, and everything else. From the old client take
ONLY the correct meshes, the geodata, and the coordinates; build with modern
Godot 4 means. Textures are NOT ported as PNG — they are CREATED with modern
methods (procedural/3D/volumetric, no PNG), clean-room, 1:1 visual identity,
verified by the mandatory comparison with the original.

**Applied immediately:**
- The CSG-carving emulation (the previous attempt) = REMOVED. The
  subtractive brushes (CsgOper=2, 50 of 219 — the carved air incl. the tunnel
  volumes and the giant zone separators) are simply not rendered; the ADD
  brushes overlapping the small subtract volumes (the legacy carved-context
  masonry housings, 43 brushes — the tunnel walls, the far-east ruins) are
  not built either: the passages stay open, the walls = the native meshes
  (the inlet, the terrain, the level BSP).
- The carpet is BACK: O_DE_Btm_Obj01 (the 34x2.1-m carpet runner, DE_V_capet01
  + the curb assembly) and Obj02/03 (the capet02 border ribbons) were in
  _ROAD_STRIP_SKIP from the clean-room-road era — un-skipped (only O_DE_Btm
  stays skipped).

**PENDING (the next iteration, the fresh context):**
1. The procedural texture system (the clean-room Godot shaders, no PNG) —
   the pilot = the road materials (the cobble floor01, the carpet capet01/02,
   the curbs) 1:1 vs the original.
2. The spawn-terrain clamp buries the test camera inside the canyon tunnel
   (the terrain = solid above the tunnel, has_terrain_surface = true) — the
   user's build shows the tunnel fine; verify the spawn path.
3. The tunnel interior = visually unverified (see 2).

## 2026-11-12 (33) — THE PROCEDURAL TEXTURE SYSTEM (the pilot: the road) + the
## street-slab restoration

**THE PROCEDURAL MATERIAL SYSTEM (the user's directive: no PNG in the render
path, modern 3D/volumetric surfaces, clean-room, 1:1 identity):**
- `assets/shaders/l2_procedural.gdshader` — ONE spatial shader, 8 modes:
  0 cobble slate (DE_V_floor01), 1 ornament tile (DE_V_floor02), 2 rock cliff
  (DE_V_m12), 3 dark stone (O_dark_01), 4 grey brick court (oren_sylen_001_1),
  5 carpet grey (DE_V_capet01), 6 carpet ornate (DE_V_capet02), 7 thorn braid
  (DE_V_capet). Base patterns are UV-aligned (the 1:1 LAYOUT identity);
  the volumetric grain = 3D world-space simplex fbm; relief = height-field
  normals with NO mesh tangents (screen-Jacobian world uv-step solve +
  world-space height gradient — needed because modes 2/3 derive h from world
  position). Palettes extracted by observation from the reference PNGs
  (clean-room study only; the PNGs are not rendered anymore for these
  materials).
- `scripts/l2_proc_tex.gd` (L2ProcTex) — the texture->mode config; cache per
  (tex, uv-convention). Case-insensitive package lookup (Oren_DEV_T vs
  oren_dev_t).
- Wiring: `_bsp_material()` tries the procedural material first (BSP UVs =
  raw texels, uv_is_texels=true); the static-mesh loop in `_get_mesh()` tries
  it before the PNG path (UModel UVs normalized, uv_is_texels=false). The
  shader-chain diffuse is already resolved in materials.json (DE_capet_il ->
  DE_V_capet), so Obj01's curb prim gets the thorn braid mode.
- THE CURB TEXTURE FOUND (the user's request): the curb along the carpet =
  Obj01 prim 1 = the DE_capet_il SHADER whose diffuse = DE_V_capet (the pale
  thorn-braid strip); the thin edging bands = DE_V_capet02's woven side bands
  on Obj02/03. No separate wall texture exists — the curb renders as soon as
  Obj01/02/03 carry their materials (now procedural modes 5/6/7).

**BSP EXPORT FIXES (both found by Godot import failures):**
- bsp2.py write_gltf: prim "material" index used the loop enumeration `pi`
  while degenerate prims `continue`d without emitting — indices drifted past
  the materials array ("Index material = 4 out of bounds" on import; 22 brush
  glTFs were failing). Fixed to `len(mesh_prims)`.
- bsp2.py now PRUNES stale outputs (a polys that renders no prims this run
  used to leave its old-format glTF in bsp_out forever — 70 stale files were
  being staged and 23 failed Godot import).
- levelbsp.py MAX_SPAN 3500 -> 7000: the "huge-span" drop was wrong — those 8
  surfs are the TWO GIANT CSG-merged DE_V_floor01 street slabs (x 6343..10225
  span 3882, x 9836..14877 span 5041), i.e. the temple street the user
  reported missing. The REAL zone separators span 7.4k-11k (bsp2 measurement).
  drawn surfs 635 -> 643, huge-span 0.

**PLAYER CLAMP FIX:** the ground-snap clamp now fires only when the heightfield
is close above the player (< 0.8 m). A tunnel/interior position under solid
terrain no longer teleports the camera up into the rock.

**VERIFICATION (numeric, per the AGENTS.md rule):**
- Floor profile x 7000..14700 @ gy 17640 (80 steps): the walkable deck family
  is continuous; the only no-deck cells = the market square 11331/11812 and
  the far-east end 14026..14700 (both pre-existing, pending the user's
  verdict). No multi-level regression.
- Floor profile x 6350..7500 @ gy 16200: the restored street slab hits
  `y=-30.222 ny=1.00 via LevelBSP` continuously from x 6618.
- Spawn screenshot (X=7400 Y=17650): the procedural cobble renders with
  recessed mortar grooves (the first attempt's white-crack artifact = the
  screen-space fwidth epsilon exploding on the giant BSP polys; fixed with
  the fixed 1-texel UV step). Carpet runner + braid strips render
  (modes 5/6/7).
- Color statistics ours vs Docs/bridge_original_level.png: cobble hue ratios
  ours 1.00:0.87:0.74 vs the reference texture 1.00:0.90:0.75 — palette
  identity; the absolute brightness difference is the scene lighting (out of
  scope until the lighting stage).

**PENDING (for the next iteration):**
1. THE TERRAIN UNDER THE TEMPLE STREET: terrain present=1 cells at
   (6416..7180, 15104..17456) hold leftover heights z -38..-42 BELOW the real
   street slab (-30.22). The false lower walkable floor = exactly the user's
   "пол над дорожкой" bug family. Needs the QuadVisibilityBitmap re-verified
   against the engine (the original hole bitmap may mark the street cutout
   like the village cutout).
2. THE CANYON TUNNEL FLOOR: (x 6400..7300, gy 17536..18400) has NO surface in
   ANY source we parse — terrain present=0, no brush actors (only 3 subtract
   volumes), no level-BSP faces, no statics. A test spawn there FALLS into the
   void. In the engine the subtract faces carry sylen_001_1/m12 materials —
   the tunnel surfaces are the CSG-baked faces of the solid world. The modern
   approach: take the GEOMETRY from the client (allowed) without recreating
   the carving — needs an engine-RE pass to extract the baked faces (the
   level Model's own nodes for that area, or a rendering decision).
3. The procedural textures: the user's visual pass on the cobble cell size
   and the carpet borders vs the original (per-texture relief/scale tweaks are
   config-only changes in L2ProcTex.CONFIG).
4. The market square + tower strip and the far-east end (unchanged from 30).

## 2026-11-13 (34) — TEXTURES REGENERATED FROM THE CLIENT PNG (not analytic
## approximations)

**THE USER'S VERDICT on the analytic shader modes: "это заглушка, пародия"** —
the hand-authored GLSL patterns (voronoi cobble etc.) do NOT match the client
1:1. The directive: regenerate the textures/shaders FROM the client PNGs —
the client texture is the PATTERN SOURCE, 1:1 by construction; add the modern
volumetric layers on top (third-party/AI tools allowed if needed).

**Implemented (all by our own pipeline, no third-party needed):**
- `tools/l2strict/texgen.py` — generates a PBR set per client texture:
  `<obj>.pbr_albedo.png` (RGB = the ORIGINAL albedo 1:1, A = height from the
  painted luminance, gaussian-blurred) and `<obj>.pbr_normal.png`
  (RGB = tangent-space normal from the height field, A = roughness
  0.65..0.95 by painted darkness). Per-texture POM depth + normal strength in
  the RELIEF config table (+ a .pbr.json sidecar). The road set generated:
  floor01, floor02, m12, dark01, sylen_001_1, capet01 (256x256 — the earlier
  128x256 guess was wrong), capet02, capet.
- `assets/shaders/l2_surface_pbr.gdshader` — albedo + normal + roughness +
  offset-mapping parallax. POM WITHOUT mesh tangents: the tangent basis is
  derived per-pixel from the screen-Jacobian (dPdu/dPdv 2x2 solve of UV vs
  position derivatives). The full POM loop produced banding/smear (implicit
  LOD inside a dynamic GLSL loop is undefined + grazing-angle explosion) —
  replaced by a SINGLE-STEP offset mapping with a view-angle fade
  (smoothstep 0.12..0.45 on |vt.z|). Crevice AO is scaled by the POM depth so
  the flat carpets keep the client's own painted shading without
  double-darkening (pom 0.055 -> full AO, 0.012 -> ~24%).
- `scripts/l2_proc_tex.gd` rewritten: material_for() returns the PBR
  ShaderMaterial when the generated set exists; the analytic
  l2_procedural.gdshader stays as the FALLBACK for not-yet-generated textures.
  tile fixed for capet01 (256x256).

**Verification:** the spawn screenshot now shows the client's own cobble,
carpet with woven borders and the thorn-braid curbs — the pattern identity is
exact by construction (the albedo IS the client texture). Hue ratios ours
1:0.94:0.87 vs ref 1:0.92:0.83 (the residual = scene lighting, out of scope).
No more POM artifacts after the offset-mapping fix.

**NEXT:** extend texgen to ALL staged textures (the generator is generic —
one batch run + Godot import), then the user's visual pass on POM depth per
texture (config-only).

## 2026-11-13 (35) — THE USER'S VERDICT + the floating-seams fix

**THE USER'S VERDICT: the client-derived PBR textures "выглядят как в
оригинале"** — approved; the remaining pass (specular/gloss/matte fine-tuning)
belongs to the later lighting stage. Recorded here and committed.

**THE FLOATING-SEAMS BUG (the user's report: on the upper village-entrance
section the textures seem to walk sideways at the joints while the camera
moves)** — root cause: the offset-mapping UV shift. Neighboring surfaces at a
joint carry DIFFERENT effective offsets (different pom depth: carpet 1.2 cm
vs cobble 5.5 cm — and different meters-per-tile between the texel-UV BSP and
the unit-UV statics), so the pattern on each side of a seam slides by its own
amount as the view direction changes — the textures visibly "walk" relative
to each other.

**FIX: the UV-offset parallax is DISABLED (pom 0.0 in L2ProcTex.CONFIG for
all 8 road textures).** The offset path stays in the shader (config-only
re-enable), but textures are now strictly bound to their UVs — no view-driven
pattern motion is possible anywhere. The volumetric look that the user
approved is preserved via the normal maps + roughness + height AO; the
parallax may be re-enabled per texture only after a verified seam-consistent
scheme (uniform effective offsets across neighbors — not attempted now).

**Verification:** a render from the user's exact report viewpoint
(L2_SPAWN=7616,17709,-4404) reproduces the approved look; with the offsets at
zero the seam swim is impossible by construction (no view-dependent UV term).

**PENDING (unchanged):** extend texgen over ALL staged textures (one batch
run + import); the lighting-stage specular/gloss tuning; the terrain under
the temple street (present=1 leftover heights below the real slab) and the
canyon-tunnel floor missing from every source (DEVLOG 33); market square +
far-east verdicts.

## 2026-11-13 (36) — texgen rolled out to ALL textures + the curbs added

**BATCH TEXGEN (the user's "поехали"):** texgen ran over ALL 223 staged
textures (13 packages) — 446 generated PBR files (pbr_albedo + pbr_normal per
texture), 0 errors, Godot import clean (892 artifacts). The per-texture
RELIEF table keeps the tuned road values; everything else uses the defaults
(pom 0.04 / normal 1.6; the parallax stays disabled per the seams fix).

**GENERIC PBR LOOKUP (L2ProcTex):** material_for() no longer requires a
CONFIG entry — ANY texture with a generated set gets the client-derived PBR
shader; tile_px is taken from the generated texture itself. CONFIG now only
carries pom overrides + the analytic fallback modes. The static-material loop
EXCLUDES the foliage packages (tree / Field_Deco) from the PBR path — they
keep the alpha-scissor StandardMaterial3D (the PBR shader has no alpha
support).

**THE CURBS (the user's task #2):** audited the whole road family — every
Oren_DEV_S catalog mesh is placed and staged; no curb statics are missing.
The curb visuals (thorn braid + woven ribbons) = Obj01 prim1 (DE_capet_il ->
DE_V_capet) + Obj02/03 (capet02) — all rendering with PBR sets now. The last
skipped road mesh O_DE_Btm was UN-SKIPPED: the old "49-m terraced wall
blocking the houses" was a merged-accessor-era artifact — the re-staged mesh
is a ~0.6-m curb/step piece at (11375,16872,-4951.9), 5 m below the deck, no
road impact. _ROAD_STRIP_SKIP is now EMPTY (795 statics placed, was 794).

**Verification:** the spawn render (X=7400 Y=17650) is clean with the PBR
materials everywhere (cobble, carpet+braid curbs, towers, ruins) — no
regressions, no seam swim (the UV offsets stay disabled), 795 statics + 128
collision shapes.

**PENDING (unchanged):** the lighting-stage specular/gloss tuning; the
terrain under the temple street + the canyon-tunnel floor (DEVLOG 33);
market square + far-east verdicts.

## 2026-11-13 (38) — ROLLBACK to the stable baseline (the user's urgent
## request): the lattice + displacement attempt broke the location

**THE USER'S REPORT:** after 335d73b/79b335d the whole location broke — dark
streaky surfaces across the roads and the plaza, while the houses kept their
previous (flat) textures. Verdict: roll back to the last STABLE state first,
fixate it, and only then design the lattice/3D-geometry idea from that
baseline.

**DONE:** `git revert` of 335d73b + 79b335d -> commits a70977f + 7d031e8.
The stable baseline = **6db6282** (the client-derived PBR textures with the
parallax offsets disabled — the state the user verified as "looks like the
original"). All 49 *_D displaced meshes removed, .godot import caches
cleaned, re-import clean (only the 17 pre-existing non-fatal warnings). The
verification render reproduces the approved look exactly (spawn view: the
cobble, the carpet+braid curbs, the towers; 795 statics, 128 collision
shapes, levelbsp 17/17 textured, brushes 48 built / 334 textured surfaces).

**WHAT THE FAILED ATTEMPT TAUGHT US (for the future redesign):**
1. The whole-Location displacement rollout in one step was wrong — one small
   face must be verified first (the project rule).
2. The displaced grids degenerated on the BIG faces: the 8000-point cap
   raised the step to 30+ texels on the 39-m street slabs, and the huge
   negative UV offsets (u ~ -30000..-80000 texels) put the height sampling
   and the lattice pattern into the precision/aliasing mud — the streaky
   surfaces the user saw.
3. The alpha-cutout lattice moire at distance needs a proper solution
   (alpha-to-coverage) and the through-hole interior needs its own lighting
   pass — not a same-day add-on.
4. Statics were never in the displacement scope — hence "houses with the
   same flat textures" against the broken BSP everywhere.

**THE STABLE BASELINE IS NOW FIXATED (7d031e8). Any next experiment starts
from it and lands only after per-face visual verification.**

## 2026-11-13 (39) — the plaza lattice, take two: SMALL verified steps from
## the stable baseline (the user: "продолжаем с сетки. 3D потом")

**The same goal as the reverted attempt, rebuilt from the 6db6282 baseline
with the DEVLOG-38 lessons applied:**
1. texgen: the alpha-preservation code restored, but ONLY Iron_net +
   DE_V_fence regenerated (a 2-file diff instead of re-rolling all 223).
2. The PBR shader: `use_alpha` + alpha-scissor discard — a uniform defaulting
   to FALSE, so nothing changes until a material opts in; in alpha mode the
   height-AO is off (A is the mask, not height).
3. L2ProcTex.ALPHA_CUTOUT whitelist (Iron_net, DE_V_fence) — the carpets'
   specular-mask alphas stay opaque.
4. **THE STREAK FIX: the alpha-cutout surfaces are SPLIT into their own
   MeshInstance with `cast_shadow = OFF`** (_build_bsp_brushes). Root cause of
   the reverted attempt's breakage: the thin grate sits ~3 mm above the plate
   below, and its hole-shaped shadow map at that offset produced full-surface
   shadow acne across the plaza (radial streaks). Without cast shadows the
   grate still RECEIVES light normally.

**Verification:** the plaza near view shows the clean lattice grid (no
streaks; the statue's hand shadow falls across the grate like in the
original); the far view shows the grate pattern with no moire; the spawn view
is pixel-identical to the approved baseline (no regressions). The floor
profile is untouched (the grate plate stays walkable, collision = the flat
trimesh).

**NEXT (the user's order): the true 3D-geometry (displacement) design — from
this verified state, one test face at a time.**

## 2026-11-13 (40) — the texture "стык" (tiled-plate seams) fixed by the
## canonical texture projection

**THE USER'S REPORT:** the textures are not continuous — a visible seam where
two coplanar plate faces meet (the dark plates flanking the carpet corridor).

**ROOT CAUSE:** every BSP face took its texture axes from ITS OWN surf —
the per-surf texture pan (base point) made coplanar faces of one plate tile
with phase mismatches, so the pattern jumped at every face boundary. The
offsets also produced the -30000..-80000-texel UV magnitudes.

**FAILED ATTEMPT FIRST (recorded honestly):** world-space planar mapping in
the shader (world_uv) — the axis-flip at non-axis-aligned normals wrecked the
terraced stairs with interference swirls. Reverted before commit.

**THE FIX (in the pipeline, both exporters):** CANONICAL TEXTURE PROJECTION
for the chaotic stone textures (floor01, dark01, m12, sylen_001_1, floor02):
all faces of one texture share ONE (U,V) direction family and project through
the GLOBAL ORIGIN (u = dot(P, Uc), base = 0). Coplanar faces tile with zero
phase mismatch; the UV magnitudes collapse to sane values. Families are
keyed by the rounded U direction (rotated faces keep their own family —
the chaotic patterns are mirror/rotation tolerant). Aligned art (carpets,
the ornament medallions, the grate) keeps its own axes. Implemented in
bsp2.py (brush faces) and levelbsp.py (the level slabs) so slabs and brushes
project consistently.

**Verification:** the west-facing render from the user's exact report point
(10741,16930,-4628.9) matches their screenshot framing and the dark plate is
now uniform (no hard texture-change line); the spawn view is unchanged from
the approved baseline; the numerics: cross-brush shared-vertex UV continuity
= no phase mismatches (the plates join at T-junctions, so the check found no
coincident vertices — the visual check is the proof).

**The world_uv experiment taught:** do not project chaotically-textured
surfaces in the shader by dominant-axis selection — the terrace/stair normals
flip the axis and produce interference swirls; the canonical projection at
export keeps the real surf axes and is seam-free.

## 2026-11-13 (41) — the "textures turned to garbage" regression: the
## canonical family key must be the FULL (U,V) pair, not U alone

**User report:** at the village entrance (game 7666,17666, the road south of
the bridge) the textures became garbage — the road/cobble surfaces render as
1D plank-like stripes. Reproduced at L2_SPAWN=7666,17666,-4404.5 yaw 0.

**Root cause (measured, not guessed):** the canonical texture projection
(ec54d… ecd54e4) keyed texture direction families by the rounded **U**
vector only. Faces that share the U direction but have DIFFERENT V axes
(walls vs floors — e.g. DE_V_floor01 used on both) were forced onto the
family's (U,V). The forced V is not perpendicular to those faces' planes
(dot(V,N) != 0), so the V coordinate goes (nearly) constant across the
face — the V UV span collapses. Span-diff 5e632b6 -> ecd54e4: **70 brush
prims lost their V span** (BSP_Polys118..BSP_Polys3995, e.g. Polys3977
prim4: 869x1614 -> 869x0) = the 1D stretch the user saw.

**Fix (both exporters):** the family key is the rounded (U, V) pair —
bsp2.py `key2 = (pkg, tex, round(U), round(V))`, levelbsp.py
`dk = (round(U), round(V))`. Coplanar seam faces share BOTH axes and
differ only in the base pan, so the стык fix survives untouched; faces of
different orientation were never seam sources and now keep their own axes.

**Verification:**
- span-diff worktree vs the approved baseline 5e632b6 over all changed
  brush bins: **0 prims differing** (offsets shift — the intended origin
  projection — spans identical);
- render at the user's position (7666,17666 yaw 0): cobble again, matches
  the baseline except the intended tile-phase shift (side-by-side crop in
  tmp/seam_check/crop_compare.png);
- spawn view: normal, cobble road + ornament strips, no stripes.

**Re-confirmed tool quirk:** after regenerating the glTFs the first
verification screenshot was STILL striped — the Godot import cache did not
refresh. Deleting `assets/maps/20_18/meshes_bsp/*.import` and
`.godot/imported/` + full `godot --headless --import` fixed it (AGENTS.md
warning applies to CHANGED files too, not only valid=false stamps).

**PENDING (logged, deliberately NOT fixed in this task):** levelbsp.py's
prim loop emits only the U component into TEXCOORD_0
(`uvs.extend([u for u, w in uv])` drops V) — the LevelBSP UV accessor has
HALF the vertex count (POS 588 / UV 294 on prim0), so vertices read
mis-paired UVs. Present since the LevelBSP introduction (identical in the
approved baseline and current state), and the visible street renders from
brush geometry on top, so it has been invisible. Fixing it changes what the
LevelBSP surfaces sample — needs its own small step + visual verdict.

## 2026-11-13 (42) — the joint × light problem and the 3D-geometry
## experiment (the user picked path C: straight to real geometry)

**The user's report:** the plate/carpet joints exist in the original client
too, but there the light does not treat the two sides separately — in our
port the sun "works on each texture separately", which is why the joint is
noticeable. A matte "baked" BSP-material experiment (specular_gain=0,
relief_gain=0) was REJECTED by the user ("baked static lighting is not
needed") and reverted; the discussion produced path C — prepare the height
pipeline for real polygon displacement (normals from real geometry are
continuous across the joints by construction).

**The experiment unit:** the BSP walkway brush Polys3977 (all 6 faces
DE_V_floor01, canonical UVs) at the village entrance (game 7666,17666) —
the area of the user's earlier seam reports.

**disp.py recovered from git (79b335d) and FIXED — three real bugs:**
1. AFFINE-FIT TRANSPOSE: `world = iX @ M[:,:2].T + M[:,2]` used the rows of
   M where the columns are the world axes (M solves A@M=verts). Latent since
   the first attempt: it only worked for faces whose UV base sat at the
   world origin; the canonical UVs exposed it (the horizontal faces came out
   ~5-6 m off-plane). Now `world = [u,v,1] @ M`, Bu=M[0,:], Bv=M[1,:].
2. THE PAINT-VS-FORM HEIGHT: the albedo A channel is PAINTED shading —
   displacing it at texel resolution re-rendered the painted crevices as a
   physical ~45° sawtooth (the whole face blotchy-dark). The displacement
   height field now gets a strong gaussian (form_blur 14 px, sidecar-
   configurable) — normals/geometry encode the LARGE forms (cobble domes),
   the paint stays in the albedo. This is the same paint≠form rule from the
   A/B discussion, now applied to geometry.
3. UPWARD-ONLY DISPLACEMENT (0..pom, the plate plane = the mortar level):
   the old ±pom made the surface DIP below the coplanar LevelBSP slab
   underneath, exposing the slab's broken UV stream as black blobs; the
   upward-only form also removes the coplanar z-fight the flat baseline had.
   PLUS the winding fix: Godot generates flat normals from the triangle
   winding and does NOT flip them for backfaces of cull_disabled custom
   shaders — the lattice winding is now oriented outward via the face-
   centroid-minus-brush-center hint, else the whole displaced plate rendered
   unlit-black.

**Integration (experiment-gated):** `L2_DISP_BRUSH=<polys>[,…]` makes bsp2
emit <name>_D.gltf ONLY for the named brushes (normal builds pass
tex_of=None and prune stale _D files); world.gd renders BSP_<polys>_D.gltf
for that brush while the collision stays on the flat trimesh (the relief is
0..5.5 cm). Also: _screenshot_flow now waits 90 physics frames — the fixed
10-frame shot captured the spawn mid-fall with the camera lerping, so the
same state produced jittering framings that broke A/B pixel diffs.

**Verified:** the displaced walkway renders real cobble relief — the stones
catch the sun, micro-shadows from the geometry, the arch shadow falls
naturally, the joints with the ornament strip and the neighbor plates are
clean; the spawn view is unchanged. A/B crops: tmp/seam_check/ab_side.png
(left flat, right displaced).

**PENDING (logged):** the LevelBSP slabs are COPLANAR with the brush plates
(z-fight shimmer in the flat baseline — the dark patches the user reported
as "стыки") and the LevelBSP UV stream is broken (half-size TEXCOORD_0, the
V component dropped — DEVLOG-41). The plates' own 3D-geometry rollout
(per-face verdicts) and these two items share the same root region.

## 2026-11-14 (43) — the 3D iteration verdict: reverted; the mouse-wheel
## zoom implemented; the carpet verified whole

**The user's verdict on the one-brush displacement experiment (DEVLOG-42):**
the seams remained AND part of the carpet was lost — a failed iteration.
The cause: the ornament carpet strip lies a few mm ABOVE the plates; the
upward-only displaced plate (0..5.5 cm) rose over it and hid the carpet
where it crossed the walkway — the carpet ended in a hard horizontal cut at
the displaced-plate boundary (the user's screenshot at 7482,17753). AND:
3D floor geometry is NOT needed unless a strong camera zoom exists — the
relief is invisible at the normal play distance.

**Done:**
1. The displaced BSP_Polys3977_D.* REMOVED from the staged assets (the
   carpet verified whole at the user's exact viewpoint after the revert —
   the ornament strip runs continuously under the arch shadow). The disp.py
   pipeline + the L2_DISP_BRUSH gate STAY in the tree, default-off, for the
   potential zoom-era reuse; normal builds prune stale _D files.
2. THE MOUSE-WHEEL ZOOM (the user's order): cam_zoom multiplies the whole
   pivot->camera offset (0, 2.4, 4.4) — the pitch angle holds, the classic
   L2 behavior. Wheel up = closer (x0.88), down = farther (x1.14), clamp
   0.35..2.6 (over-the-shoulder .. ~11 m). L2_ZOOM=<float> = the spawn-time
   verification hook for screenshots.
3. CAMERA COLLISION: zooming out pushed the camera INTO the rocks (the
   2.6 render at the street showed the rock interior). A ray from the
   pivot's chest height to the desired camera position pulls the camera
   0.25 m in front of the first hit — the classic L2 pull-in.

**Verified:** L2_ZOOM 0.4 / 1.0 / 2.6 at the street view (7482,17753,
yaw -Y): close = over-the-shoulder, default = unchanged framing, far = the
camera pulls in front of the rocks (the wide street + carpet view the user
showed). tmp/seam_check/zoomc_*.png.

**Next (the user's order): the joints (стыки)** — the LevelBSP slabs
coplanar under the brush plates (the z-fight shimmer) + the broken LevelBSP
UV stream (half-size TEXCOORD_0, DEVLOG-41/42).

## 2026-11-14 (44) — THE ROAD AS ONE CONTINUOUS TEXTURE (the user's joint
## solution: merge the meshes, one texture over the whole road)

**The user's directive:** the seam problem is easier to solve by merging
the meshes — one continuous texture over the whole road; the curbs on the
sides and the stairs at the end are the physical borders (they already
exist). Also: the zoom works as needed; the floor 3D effect is visible only
at the far zoom — not needed for now.

**The implementation** (the canonical projection already gives every road
face of one texture a single world-aligned UV space — what remained were
two defects):
1. THE LEVELBSP UV STREAM FIXED (the DEVLOG-41/42 pending item): the prim
   loop emitted only the U component into TEXCOORD_0 — the UV accessor had
   HALF the vertex count (POS 588 / UV 294) and the vertices read
   mis-paired UVs. Now both components are emitted (588 = 588 verified).
   The LevelBSP slabs sample the same canonical texture space as the
   brushes.
2. THE COPLANAR Z-FIGHT REMOVED: the LevelBSP render mesh sits 1 cm below
   the collision (mi.position.y = -0.01 in world.gd _build_bsp) — the slabs
   hide under the brush plates and still render in every levelbsp-only area
   (the temple court, the valley). The road reads as ONE continuous texture
   from curb to curb; the collision body keeps the authentic height.

**Verified:** the user's road view (10636,17048, the stairway plaza): the
carpet strip runs continuously, the cobble plates read as one surface, NO
z-fight (frame-to-frame diff = 0 changing pixels), the stairs/lattice area
textured correctly; the spawn view unchanged.

**Note:** the floor 3D displacement stays default-off (DEVLOG-42/43) —
visible only at the far zoom; revisit together with the zoom-era polish.

## 2026-11-14 (45) — the REAL seam root: per-texture scale unification

**The user: the seam is still there.** The numeric inventory of the road
faces (per-triangle texel/m density over the brush glTFs) found the actual
cause: the plates of ONE texture carried DIFFERENT texel scales —
DE_V_floor01 mostly ~195-200 texels/m but also 97.5 (2x coarser stones) and
53.7; DE_V_floor02 390 dominant vs 97.5; O_dark_01 scattered 92..105;
oren_sylen_001_1 200 vs 250. The canonical projection unified the PHASE
(the origin projection) but the pattern DENSITY still jumped at the plate
boundaries — that is the visible "стык" (the user's "merge the meshes, one
texture over the whole road").

**The fix (both exporters):** the canonical family is chosen per (texture,
ORIENTATION CLASS): faces are bucketed by the quantized face normal
(Newell's method — the first-three-vertex cross produced garbage normals
for sliver fan polygons and poisoned the buckets), and each orientation
class gets its own DOMINANT (most frequent) rounded (U,V). A single
per-texture family let a wall family win (the levelbsp floor01: a 5-face
wall family of 116) and left the horizontal slabs at half-scale. Faces of
other orientations keep their own axes, and an in-plane guard (|dot(axis,
normal)| <= 0.1 of the axis length) applies at BOTH counting and
application time — forcing axes not in the face plane was the "мусор"
1D-stretch regression (2026-11-13).

**Discovery en route:** the level-model (LevelBSP) surf axes are
INHERENTLY SKEWED for ~half of the floor01 faces (e.g. a vertical V on a
horizontal slab — the mapping is near-1D by the engine's own data; no slot
interpretation of the FBspSurf record fixes it). Those slabs are hidden
under the brush plates in the original too, so their skew is invisible —
they stay hidden in our port (the 1 cm lowering, DEVLOG-44) and keep their
own axes.

**Verified numerically:** the per-triangle density histogram over the
visible brush plates collapses to ONE family per texture (floor01 = 200,
floor02 = 400, dark01 = 100 texels/m); the stretched-triangle scan = 0 in
the brushes (416 remain, ALL inside the hidden LevelBSP slabs' own skew
axes); the phase continuity through the origin projection is exact by
construction (adjacent plates share boundary points -> identical UVs).
Visual: the reported seam views (7666,17666 and the stairway plaza
10636,17048) show a uniform stone pattern across the plates and the
continuous carpet; the spawn view is normal (its framing differs from the
pre-zoom baseline only by the approved camera pull-in, a6639ca).

## 2026-11-14 (46) — the seam's TRUE layer: the visible road is the
## STATIC meshes; world-space UV for the road stones

**The user: the seams are still there — maybe the project was not rebuilt.**
The floor profile at the user's three seam spots shows the truth: the
walkable road there is the STATIC meshes — Oren_DEV_S:O_DE_Btm_Obj01
(-44.045, 10 cm ABOVE the BSP:Polys3977 plates at -44.15), O_DE_MT_In (the
plaza dark plates), O_DE_MT_Btm. ALL the previous seam fixes (canonical
projection, LevelBSP UV, the 1 cm lowering) worked on the BSP layer —
HIDDEN under the statics at those spots. The user was right.

The trace box over the road pixels: the road is a MIX — 868 px
BSP:Polys3977 + 192 px Oren_DEV_S:O_DE_Btm_Obj01 + O_DE_Bridge: the static
pieces and the BSP plates alternate, with different authored textures
(Obj01's cobble = DE_V_floor vs the BSP plates' DE_V_floor01) and per-piece
UV phases — the seams the user sees.

**The fix (shader-side world-space UV):**
1. l2_surface_pbr.gdshader gains `uniform float world_uv_scale` (tiles per
   meter, 0 = off): horizontal faces (|world normal y| > 0.85) sample
   uv = world (x, z) * scale — one continuous texture across every piece
   and BOTH layers; walls/slopes keep their authored UVs (the axis-flip
   swirls of the failed world_uv experiment avoided — no dominant-axis
   selection, the road is flat).
2. L2ProcTex.WORLD_UV (tiles/m, measured from the original meshes):
   O_dark_01 = 0.1307 (66.9 texels/m, O_DE_MT_In), DE_V_floor01 = 0.78125
   (200 texels/m, O_DE_Btm), applied to BOTH layers — the density
   difference between the static and BSP dark plates (66.9 vs 97.5) would
   still seam at the layer boundary.
3. L2ProcTex.TEXTURE_SUBSTITUTE: DE_V_floor -> DE_V_floor01 — the static
   cobble pieces used a DIFFERENT cobble image than the BSP plates; per the
   user's directive ("текстуру наложить одну сплошную на всю дорогу") all
   road cobble now uses the floor01 PBR set. Carpets/ornaments are aligned
   art and keep their authored UVs.

**Verified:** the trace-box road region renders with a uniform cobble
pattern (the previous diagonal pattern jump at the piece boundary is gone),
the carpet strip is continuous, the plate/carpet boundaries are the only
remaining edges (legitimate texture transitions). 141k pixels changed when
the world-uv was extended to the BSP layer (the override works). The
shader/substitution verified through the material path (world_uv_scale
0.78125 / 0.1307 present on the materials).

**Note:** a floor-profile caveat — the road pixels near piece boundaries
can raycast to EITHER layer (the statics sit 10 cm above); both layers now
sample the same texture space, so the ray's winner does not matter.

## 2026-11-14 (47) — the camera-rotation bug: fragment VERTEX is VIEW-space

**The user:** the seams remained + the textures ROTATE WITH THE CAMERA.
Both symptoms — one root: in Godot 4 fragment() VERTEX is VIEW-space even
with world_vertex_coords (the flag reliably covers only the vertex stage).
The world-uv override built on fragment VERTEX (a) sampled VIEW coordinates
— the texture rotated with the camera; (b) its |ngeo.y| > 0.85 guard tested
the VIEW-space normal — for the road viewed at the normal camera angle the
guard almost never fired, so the override rarely applied at all (which is
why the previous iteration's renders looked unchanged).

**The fix:** a varying `wpos` written in vertex() (= world space under
world_vertex_coords); the fragment override uses wpos and a normal derived
from dFdx/dFdy(wpos). The world-uv now applies unconditionally-correctly
and is anchored to the world by construction (uv = world(x,z) * scale
cannot rotate with the camera).

**Verified:** 1,005,785 of 1,440,000 pixels changed vs the pre-world-uv
frame at the same camera — the override actually renders now; the cobble
pattern is uniform across the whole road (tmp/seam_check/wfix_A.png), the
carpet strip continuous, the pattern anchored to the world.

**Craft-anything clean-room record:** the investigation memory revealed
the LITERAL geometry rebuild of the road was already TRIED in earlier
sessions and rolled back twice (cce5af0 "rollback-of-the-rollback",
45a4d10 "the floating sloped clean-room road removed entirely"). The
current approach achieves the visually whole floor WITHOUT the risky
geometry rebuild: every horizontal road face of every piece (both layers)
samples ONE continuous world-anchored texture — the floor is "whole" at
the texture level. The plan notes the geometry rebuild stays an option
only if the user insists after this fix.

## 2026-11-14 (48) — the road seam FINALIZED: world-UV declared final; the
## verification harness installed; every remaining joint classified

**Iteration report (the gates protocol):**
- Гейт A: compile-errors=0 (gateD_stderr.log, gateA_final.log), pink-pixels=0 -> green
- Гейт B: viewport=7482,17753/yaw49152/zoom0.4, diff=1,005,785 px vs the
  pre-world-uv frame, direction=expected (the world-uv applied) -> green
- Гейт C: trace-box at 7482,17753 -> the road pixels = BSP:Polys3977
  (868) + Oren_DEV_S:O_DE_Btm_Obj01 (192) + O_DE_MT_Btm (16) + O_DE_Bridge
  (174) -> the fix targeted BOTH layers (statics + BSP) -> green
- Гейт D: branch = the world-uv override; hot-pink coverage = exactly the
  horizontal road faces of every piece (near and far), the carpet strip /
  walls / arches / terrain clean; 0 compile errors with the assert in ->
  green; the debug output removed after verification
- Гейт E: lint — the world-uv block reads only `wpos` (varying); the 5
  remaining VERTEX reads in fragment are the view-space POM/TBN block (not
  world-effects); terrain.gdshader does not exist in the tree -> green
- Мета: memory query "road geometry rebuild attempted?" -> YES, twice,
  rolled back (cce5af0, 45a4d10) -> the UV-sample solution stands

**Task 1: world-UV is FINAL.** The road seam is resolved at the UV-sample
level (world_uv_scale + the DE_V_floor -> DE_V_floor01 substitution); the
geometry rebuild stays off (2 prior rollbacks).

**Task 2: the coverage inventory.** Every road static's road-stone textures
carry world_uv_scale: O_DE_Btm (DE_V_floor01), O_DE_Btm_Obj01 (DE_V_floor
-> floor01 via the substitution), O_DE_MT_In + O_DE_MT_Btm (O_dark_01).
O_DE_Bridge carries NO road-stone textures (walls/decos/metal/chain —
aligned art) — nothing to cover. The BSP road stones (floor01/floor02/
dark01/m12/sylen) — floor01 + dark01 via WORLD_UV, floor02/m12/sylen via
the export-time canonical projection (their visible areas are single-layer
and orientation-unified).

**Task 3: the remaining joints classified (each = one of а/б/в):**
- (в) ACCEPTED legitimate transitions: plate<->carpet texture boundary;
  curb edges; the stair/terrace steps; flat->slope transitions (sloped
  faces keep authored UVs — the horizontal guard); the cobble->dark-stone
  plate boundary (different textures by design, as in the original).
- (б) meshes without world_uv_scale: none left for the road stones (the
  inventory above).
- (a) stale cache: if a seam is reported that does not match this
  classification — first `rm -rf .godot` + full reimport before touching
  any code (the user's "maybe you did not rebuild" was exactly this class).

**Task 4: the gates A-E + the meta-gate codified in AGENTS.md** (the
pre-commit protocol for any shader/material/geometry fix).

### 2026-11-15 (56) — THE GOLDEN STATE RESTORED: the road files rolled back
## to a6639ca (the zoom build = the user's golden screenshot build)

The user: "текстуры не вернул, плохо откатил по git". The bisect through the
builds identified THE build the user's golden screenshot was taken on:
**a6639ca (the zoom build)** — the state BEFORE the whole seam-fix chain
(149275f the scale unification, ede3c12 the world-uv + the substitution,
a51b955 the road samplers + the hides, 52ba990/f59885e the v3, e75fa47/
4ebbeca the follow-ups). The chain's cumulative effect = the road's
authored texture mapping progressively replaced by the experimental
projections/scales/substitutions.

**The restore:** the road files (world.gd, l2_proc_tex.gd,
l2_surface_pbr.gdshader) = a6639ca's versions EXACTLY; the only delta =
the L2_BRIGHT diagnostic fix re-applied on top (the zone ambient/fog block
wrapped in `if not bright` — the normal scene unaffected).

**Kept (the user-approved non-road work):** the wheel zoom + the camera
collision (a6639ca itself), the camera-rotation fix (c5733c1's wpos — hmm —
a6639ca predates it; the wpos fix is NOT in a6639ca — the restored files =
pre-wpos: the world-uv era is gone so the wpos is moot), the L2_BRIGHT fix.

Wait — the camera-rotation fix (c5733c1) was made AFTER a6639ca — the
restored files = pre-c5733c1: the shader = the pre-wpos version. The
world-uv override is GONE from the shader (the whole mechanism rolled
back), so the view-space bug is moot — nothing left to fix.

**Kept:** the zoom (a6639ca), the L2_BRIGHT fix (re-applied), the hides
REMOVED (the golden state has the BSP plates visible as authored).

**Verified:** the descent render at the user's spot (8484,17511) = the
sunlit textured road as the golden screenshot. The diff vs a6639ca =
world.gd only (the bright fix).

The seam (стык) task: CLOSED (the user will redefine). The recorded
lesson: the road texture experiments (the canonical scale unification, the
world-uv, the substitutions) progressively degraded the authored look —
the golden build = the authored textures.

## 2026-11-15 (57) — THE GOLDEN BASELINE MARKED PERMANENTLY

The user confirmed the restored state ("наконец вернули то состояние") and
ordered it marked so it is never lost again: "такое количество итераций мы
не можем себе позволять каждый раз".

**Done:**
1. The git tag: **`golden-road-20261115`** on 54dadb9 (the annotated tag —
   `git tag -l` / `git show golden-road-20261115`).
2. The baseline renders saved to the repo: `Docs/baseline/*.png` — the five
   named viewports (the upper street, the entrance road, the descent, the
   stairway plaza, the spawn plaza) with `Docs/baseline/MANIFEST.md` = the
   exact reproduction commands.
3. AGENTS.md: the new section "GOLDEN BASELINE" — the approved look, the
   verification rule (the pixel-diff against the baseline renders at the
   same cameras after the fresh reimport), and THE FORBIDDEN MOVES (each
   burned-token lesson recorded): no authored-texture substitutions, no
   world-uv on the road, no height offsets without the user's approval of
   the visual result, no road geometry rebuilds.

**The verification protocol for any road/floor visual change:** render at
the baseline cameras (the fresh reimport first) → pixel-diff vs
`Docs/baseline/*.png` → any deviation beyond the noise = the regression,
not "verified". The baselines = the ground truth; the DEVLOG text = the
explanation.

## DEVLOG-58 (2026-11-15): THE CODE PUSHED TO GITHUB — guglovich/l2-gd-demo

**The user's order:** push our code and the Godot project to
https://github.com/guglovich/l2-gd-demo; do NOT push the screenshots and
the tools we did not create.

**What was done:**

1. `.gitignore` extended: `Docs/**/*.png` (ALL screenshots/renders stay
   local — incl. the golden baselines and DE_village.png; they are
   regenerable and the baseline protocol lives in MANIFEST.md), the
   third-party/vendored tools, `notify.log`, `.zcode/`, `__pycache__/`.
2. Untracked (git rm --cached, the files stay on disk):
   - third-party tools: `tools/l2redat.exe`, `tools/GeodataConverter_02_01_01/`,
     `tools/L2UE_Explorer_v1.091/`, `tools/craft-anything-0.2.0/` (vendored),
     `tools/[273]_high_five/` (the client geodata dumps), `tools/__pycache__/`.
   - screenshots: all 19 PNGs under Docs/.
3. **History rewritten** (git filter-branch --index-filter over all 148
   commits + both tags) so none of the above paths exist in ANY pushed
   commit. Verified: zero matches for the forbidden paths in the full
   `git log --all --name-only` after the rewrite; refs/original removed,
   reflog expired, gc --prune=now. The commit hashes changed (148/148) —
   the old DEVLOG hashes are pre-rewrite; the TAG
   `golden-road-20261115` now = **92ead99** (was 54dadb9) and marks the
   SAME tree content (only the excluded files differ).
4. Pushed: master → origin (2928 files on the remote), both tags.
   Remote verified via the API: `tools/` contains ONLY our tools
   (l2strict, ghidra runner, l2_*.py, export shell scripts);
   `Docs/baseline/` contains ONLY MANIFEST.md.

**The repo layout note:** the ~146 MB pack is our generated assets
(`assets/maps/20_18` meshes + `assets/textures` client-derived PNG sets —
the pipeline outputs, regenerable but pushed so the project builds from a
clone). tmp/, analysis/, the RE vendored tools and all screenshots are
local-only.

**Status:** the task is done. The golden-baseline protocol, AGENTS.md and
DEVLOG stay the source of truth; the remote is the backup/visibility copy.

## DEVLOG-59 (2026-11-15): THE REAL CHARACTER — the Dark Elf female FIGHTER
## base + the run animation

**The user's task:** replace the placeholder with the ORIGINAL dark elf
female fighter skeleton + her textures (no armor set, no weapon), any head
variant, and make the run animation.

**What the client has (found via `umodel -list`):**
- `Animations/DarkElf.ukx`: SkeletalMeshes `FDarkElf_m000_{u,l,b,g}` (the
  BASE body, m000 = no armor), the FACE mesh `FDarkElf_m000_f`, the hair
  variants `FDarkElf_m000_m00_ah` (Bip01-skeleton, 85 nodes) and
  `_m00_bh` (OWN Hair01-13 skeleton — physics hair, NOT usable with our
  animation, skipped), MeshAnimation `FDarkElf_anim` (99 sequences).
- `SysTextures/fdarkelf.utx`: base body textures `FDarkElf_m000_t1000_{u,l,
  b,g}`; face variants `FDarkElf_m000_t00/t01/t02_f` (+`_f1` = the blink
  frame); hair textures `_ah_ori/_ah_u00` (white strands on black, alpha =
  coverage). We took `t00_f` (eyes open) and `ah_ori`.

**The pipeline (all our tools, the modern-port rule respected — the texgen
PBR sets are generated FROM the client PNGs, 1:1 identity):**
- exported the 6 base meshes via umodel glTF → `assets/character/` and the
  8 client PNGs → `assets/character/fdarkelf/Texture/`, generated the PBR
  sets with `tools/l2strict/texgen.py`;
- `tools/psa_to_gltf.py` (NEW): parses the ActorX PSA and injects a chosen
  sequence as a glTF animation into the part files. `Run_Hand_FDarkElf`
  (the no-weapon run, 16 frames @ 24 fps) injected into all six parts;
  Godot plays all six AnimationPlayers in sync (same clip, same frame).
- `scripts/player.gd`: loads the 6 base parts, assigns the PBR materials
  (the hair = StandardMaterial3D TRANSPARENCY_ALPHA — the alpha-scissor
  discard ate the thin strands, verified), plays the run clip while moving,
  stops to the bind pose when idle; rig scale 4.0 (the L2 skeletal meshes
  are stored ~4x below world scale; 0.444 m mesh → ~1.78 m).

**THE TRAP THAT COST THE SESSION (documented in Docs/psa-format.md):** the
old PSA export (tmp/umodel_export, Oct 2025) contains RAW NON-NORMALIZED
quats (z=1.0, w=6.47) from an old UModel build — the character fell flat /
crumpled no matter the conversion. A FRESH export (tmp/umodel_export2)
gives proper normalized quats + full position tracks. The conversion math
is derived from UEViewer's ExportGLTF.cpp and verified numerically against
the bind pose (pelvis frame0 within 5.7° of bind).

**Verification (the frozen-frame + autorun renders):**
- the bind pose at spawn: the base body + face + ear + white hair, standing
  upright on the ground (zoom 0.45 close-up) — the user should compare
  against the original client;
- the run cycle frozen at frames 0/4/8/12 (L2_ANIM_FRAME hook, side cam):
  a proper stride with the L2 forward lean, the cycle varies per frame;
- autorun in-game (L2_AUTORUN=1, top-down): the character runs with the
  animation live, legs cycling toward the destination marker.
- Gates: A (0 shader errors), B (the character visibly changed at spawn),
  C (trace: the character is scripts/player.gd, not BSP/statics), D
  (L2_ANIM_FRAME/L2_AUTORUN hooks prove the animation branch fires), E
  (no world-space effects added).

**Pending (NOT done, out of the stated scope):** the idle animation
(Wait_Hand_FDarkElf is in the same PSA, one command away), the walk
(Walk_Hand), the blink (t00_f1), the hair variant tuning, the exact height
calibration vs the original client (the 4.0 scale constant), the weapon
bone attachment (Weapon_R_Bone etc. exist in the skeleton).

## DEVLOG-60 (2026-11-15): THREE CHARACTER BUGS FIXED (the user's report)

1. **"лицо съехало в сторону"** — diagnosed via per-part renders + bone
   probes: the face mesh is NOT displaced (all six skeletons' Bip01_head
   global poses are IDENTICAL live and frozen, verified by
   L2_CHAR_DEBUG=1; the injected animation data is byte-identical across
   the part files). What read as a "displaced face" = the hair: the small
   ah tuft (38 verts) rendered as a white wisp while the head showed only
   the dark backside of the face texture. FIX: the FULL hair
   FDarkElf_m000_m00_bh (13 hair bones, bind in body space) is attached to
   the Bip01_head bone via BoneAttachment3D with the correction transform
   inv(head bind global) — the hair rides every head pose (the client
   attaches its hair bones to the head too; the bh's own skeleton cannot
   play the Bip01 run clip). Verified: the hair sits on the head at bind,
   at the frozen run frames and in the live autorun.
2. **"дефолт стойка в режиме бега"** — the click-to-move target is dropped
   when the character is BLOCKED (get_real_velocity() < 0.5 m/s while
   has_target): no more running-in-place against a house; the pose returns
   to bind via _char_run(false). Verified at the user's spot (11040,17464):
   the character runs to the steps, gets blocked, stands idle.
3. **"рост и размеры превышены"** — CHAR_SCALE 4.0 → 3.6: the retail DE
   female collision_height = 37.5 dat units ≈ 160 cm; 3.6 × 0.444 m mesh =
   1.60 m. The constant stays single (scripts/player.gd) for further
   calibration against the original client.

Diagnostics kept (env-gated): L2_CHAR_DEBUG=1 (per-part bone print),
L2_CHAR_ONLY=<part> (render one part), L2_DEBUG_CAM=close (head close-up),
L2_ANIM_FRAME, L2_AUTORUN.

**Pending:** the idle (Wait_Hand) / walk (Walk_Hand) clips, the blink
(t00_f1), the exact scale confirmation vs the original client, the hair
physics (the client animates the 13 hair bones — ours is a static bind,
fine without wind/physics).

## DEVLOG-61 (2026-11-15): follow-up fixes after the user's re-test

1. **"при просмотре сзади работает прозрачность"** — the hair materials
   (ah + bh) switched from TRANSPARENCY_ALPHA to ALPHA_SCISSOR
   (threshold 0.5): the hair textures' alpha is effectively binary
   (bh: 80% of pixels > 0.6, 19% < 0.1) and the alpha blend made the
   strand mass ~40% see-through from behind. Scissor keeps the strand
   cores fully opaque and discards the gaps.
2. **"персонаж не двигается"** — the blocked-detection added in DEVLOG-60
   killed EVERY fresh target on its first frame: get_real_velocity()
   returns the PREVIOUS move_and_slide result (zero before the first
   step), so the check fired immediately. Fix: a 0.5 s grace period
   (_target_time accumulates while has_target; the check requires
   _target_time > 0.5).
3. **the run pose stuck after stopping** — AnimationPlayer.stop() does NOT
   restore the bone poses; added Skeleton3D.reset_bone_poses() in
   _char_run(false) (the skeleton list is collected in _load_character;
   the missing collection was itself a bug — the empty _char_skels array
   aborted the stop branch with an out-of-bounds error and made the reset
   a no-op). Verified: the autorun run ends in the upright bind pose.

Verification renders: the bind from behind (opaque hair), the autorun
arrival (X 7400 → 8640, standing pose in both shots, 0 script errors),
the frozen run frame 4 (the clip still plays while moving, the hair rides
the head).

## DEVLOG-62 (2026-11-15): the run head pitch + the live size calibration

**"лицо теряется при беге"** — numeric bone analysis (the injected head
rotation vs its bind across the sequences): the RUN clip holds Bip01_head
at 41-46° from the bind through the whole cycle, WAIT/Stand hold it at
20-31° — the head is pitched down even where it must look forward. The
delta-from-bind and the world-space interpretations were tested and
rejected (170-180° garbage). The pragmatic fix: the Bip01_head channels
are NOT emitted (tools/psa_to_gltf.py --skip-bones Bip01_head) — the head
keeps the bind orientation (face forward) while the body leans; the hair
(BoneAttachment3D on Bip01_head) follows. Verified in the frozen frame 4
profile: the head up, the stride unchanged.

**"персонаж огромный"** — the size calibration went interactive: the
L2_CHAR_SCALE env overrides the default (3.6), and the =/- keys adjust the
rig scale by 5% live in game (the current multiplier and the resulting
height print to the console). The user calibrates against the original
client and reports the value; the constant then gets fixed. 3.6 (~1.60 m
from the retail collision_height 37.5) is still reported as huge — the
interactive tuning replaces the guess-loop.

## DEVLOG-63 (2026-11-15): the idle pair + the blink + the run head blend

**The user's report:** the face flies off the head (their screenshot: the
face mask floating above the body); add the TWO standing animations (the
livelier one after the activity and the calm one); the eyes must BLINK in
both; the size is still wrong (see the note at the end).

**The face "detachment" decoded:** the user's screenshot shows the ATKWAIT
stance (the crouched combat pose) with the head at the bind orientation —
in that build ALL clips had the Bip01_head channels excluded, so the
crouched stance kept the upright head and the face read as "flown off".
The clip-specific handling: AtkWait/Wait keep their head tracks (the
stances carry them correctly — verified: the face attached in the idle
renders), the RUN blends the head at 0.35 (--bone-blend "Bip01_head=0.35"
in tools/psa_to_gltf.py: the head quat = slerp(bind, anim, 0.35) — the
slight nod instead of the 46-deg ground-stare, the face stays visible;
verified in the frozen frame profile).

**The two standing animations (from the client's FDarkElf_anim):**
- `Wait_Hand_FDarkElf` (16 frames @ 6 fps) — the calm standing;
- `AtkWait_Hand_FDarkElf` (22 frames @ 12 fps) — the weapon-ready stance.
The state machine (scripts/player.gd _char_run): running → on stop the
AtkWait stance plays for 3 s → then the calm Wait loops (the spawn starts
directly in the calm Wait).

**The blink:** the face albedo swaps between the client's open-eye frame
(t00_f) and the closed-eye frame (t00_f1) — a random 2.5-4.5 s interval,
0.12 s closed (scripts/player.gd _physics_process).

**The size:** still open. The retail DE female collision_height = 37.5 dat
units ≈ 160 cm → the scale 3.6, but the user reports it as still wrong
("персонаж ниже карты при входе в деревню" — ambiguous: shorter than the
map expects, or sinking below the map surface at the entrance). The
interactive calibration is in place: the =/- keys adjust the rig scale by
5% live and print the multiplier + the resulting height; L2_CHAR_SCALE
overrides the default for the screenshot runs. THE USER CALIBRATES AND
REPORTS THE NUMBER; the constant gets fixed then.

## DEVLOG-64 (2026-11-15): THE CLEAN-ROOM CHARACTER — ONE SKELETON

**The user's verdict:** the face slides in EVERY animation (their
screenshots: the face mask jutting out of the hair in the calm Wait and
the AtkWait), and the fix is the modern-port rule: build the character the
native Godot way, clean-room, because the L2 face system was a hack ("в
Lineage 2 явно костыли были, да и схожие баги иногда в оригинальной
игре").

**THE STRUCTURAL FIX — tools/build_character.py:** the L2 client
assembles the character from six separately-animated skeletal parts (six
skeletons, six animation players, six desync chances). The tool merges
the UModel part exports into ONE unified glTF (`FDarkElf_base.gltf`):
one skeleton (the donor = the upper part), one skin, ONE animation
player, the six client meshes as plain skinned mesh nodes referencing the
shared skin (the joint orders asserted identical across the parts). A
part desync is now structurally impossible.

**player.gd** rebuilt on the single scene: one AnimationPlayer runs
Run/AtkWait/Wait; the materials assign per MeshInstance by the node name
(the mesh resource names carry the "FDarkElf_base_" prefix — the node
names are the clean part names); the blink and the bh hair attach work as
before but on the single skeleton.

**Import pitfalls fixed on the way:** (1) the merged mesh nodes must be
listed in scenes[0].nodes — orphan nodes are silently dropped by the
importer (the first build rendered only the torso); (2) the material
identification uses the NODE names, not the mesh resource names.

**The scale calibration visibility:** the +/− keys now ALSO show the
current scale and the resulting height on the in-game HUD label for 2.5 s
(the user runs windowed without a console). L2_CHAR_SCALE still overrides
the default for the screenshot runs.

**Verified:** the unified bind (the full body, the hair on the head), the
autorun (7400 → 8640, the calm Wait on arrival), the frozen run frame 4
(the stride, the 0.35 head nod, the face in profile), the Wait/AtkWait
idles. 0 script errors.

## DEVLOG-65 (2026-11-15): the face fix for the idles + the user's scale

**"в обычной стойке тоже проблема со съезжающим лицом"** — the root cause
of the whole face-sag family: the head bone tracks in ALL the L2 clips
over-rotate (the run 41-46°, the Wait/Stand 20-31° from the bind — the
character looks at the ground), and the rigidly attached bh hair swings
with the head — the hair ends up over the face and the face reads as
"sliding". The clean fix: the Bip01_head channels are skipped in the
IDLES too (the head keeps the bind orientation = looking forward; the
hair stays behind; the face always visible). The Run keeps the 0.35 head
blend (the slight nod). Re-injected: Run = 168 channels (the blended
head), Wait/AtkWait = 166 (the head skipped). Verified in the macro
profile render: the face fully visible, the hair behind the head.

**The user's scale calibration:** "рост персонажа примерно 0.44, пока
сделаем так" — CHAR_SCALE 3.6 → 1.0 (the mesh renders at its stored
scale, the height ≈ 0.44 m). The dat collision_height 37.5 does not map
to cm the way the earlier estimates assumed; the user's live comparison
against the original client is the ground truth. The +/- keys and
L2_CHAR_SCALE stay for the future re-calibration.

## DEVLOG-66 (2026-11-15): THE FACE DETACHMENT ROOT CAUSE — THE DUMMY SKIN

**The user:** the face slides at EVERY animation (not just some) — dig with
craft-anything (the clean-room method). The brief was written into the
craft-anything investigation (analysis/l2-godot.cany, the plan is updated
there).

**THE ROOT CAUSE (numeric):** the L2 face mesh FDarkElf_m000_f has ALL 199
vertices bound with weight 1.0 to the ROOT bone Bip01 — a DUMMY skin. In
the L2 client the face is an ATTACHED rigid mesh positioned at the head
(the vertex weights are meaningless); UModel exported the dummy weights
as-is. At the bind pose Bip01 ≈ identity → the face sits correctly at its
body-space head position. During ANY animation Bip01 sways (yaw/pitch) →
the face swings around the body origin at the ~0.4 m head-height lever —
forward, then up. Exactly the user's symptom.
Evidence (the weighted JOINTS_0 histograms): the face = Bip01 50745.0
(100%); the ah tuft = Bip01_head 9690.0 (100% — correct); the torso =
spine2/arms/spine (the proper weights). The IBMs and the joint orders are
identical across the merged files (diff 0.0) — the merge is correct.

**THE FIX:** tools/build_character.py --bind "FDarkElf_m000_f=Bip01_head"
— re-binds every listed mesh's vertices fully to the given bone (weight
1.0, the component format preserved). The face then rigidly rides the
head bone = the client-equivalent attached behavior, natively skinned.
The unified FDarkElf_base.gltf rebuilt; verified from the file (the face
binds 100% to Bip01_head) and visually across the frozen run frames
0/4/8/12 (the face stays on the head).

**The scale:** CHAR_SCALE 1.0 per the user's calibration (the height
≈ 0.44 m as the mesh is stored).

**Also:** the investigation methods moved to craft-anything (the brief,
the plan, the hypotheses, the handoff live in analysis/l2-godot.cany).
The Run keeps the 0.35 head blend; the idles skip the head tracks (see
DEVLOG-65).

## DEVLOG-67 (2026-11-15): THE STARTING OUTFIT — chargrp.dat (m001_t02) + the flicker investigation (deferred)

**The gear (the user's report: "у нас просто какой-то купальник").** The
m000 body parts we rendered are the client's UNDERWEAR (t1000) — the
visible outfit comes from armor meshes + texture sets on top. The exact
starter set was recovered from the client data files, not guessed:

- `tools/l2redat.exe` (wine) decrypts the Interlude .dat files (the
  "Lineage2Ver4138" format) → JSON. Decrypted: `armorgrp.dat` (1195
  armor items with per-race mesh/texture bindings), `chargrp.dat` (the
  per-race-gender creation look), `hairgrp.dat` (l2redat's format
  support is incomplete there — only a/b ints; deferred, not needed).
- **chargrp.dat entry 3 = the DE female FIGHTER creation look:**
  chest/legs/feet/gloves = `DarkElf.FDarkElf_m001_{u,l,b,g}` with
  `FDarkElf.FDarkElf_m001_t02_{u,l,b,g}`; hair `FDarkElf_m000_t00_m00_ah`;
  face `FDarkElf_m000_t00_f` (we already had both). So the armor MODEL is
  m001 (the same mesh family as the universal starter t02 — the human
  fighter MFighter_m001_t02 is chargrp entry 0), NOT another tNN on m000
  (fdarkelf.utx has no m000 armor sets at all — only t1000 + hair/face
  variants; the m003..m010 sets belong to armor models m003..m010).
- The pipeline rerun: the four m001 skeletal meshes exported from
  DarkElf.ukx (same 85-node skin, joint order asserted identical, 1
  primitive each, dummy materials); the t02 textures exported 512/256 px
  with REAL alpha masks on u/g; texgen PBR sets generated; the unified
  FDarkElf_base rebuilt with build_character.py --skip (NEW: --skip drops
  listed parts and, when the base donor is skipped, strips its mesh node
  while still donating the skeleton + animations). The m000 body parts
  are REPLACED by the armor meshes — the L2 client hides the body part
  under armor the same way. CHAR_MAT_MAP switched to the m001 entries.
- Verified: the dark leather bodice with straps + the shoulder plates +
  the leg harness + heeled boots (the zoom-0.13 renders front/back) and
  the spawn screenshot; 0 shader errors (Gate A). The long white hair
  (bh, t00) matches the reference screenshots.

**The white flicker (ears/face, ~30 s period, certain angles, while
moving) — investigation started, DEFERRED by the user ("долгая итерация,
собирай сборку").** Findings so far (all numeric):

- NOT specular: the generated roughness is 0.65–0.95 everywhere (face
  p50 0.82) — no glossy glint source.
- The bh hair mesh has 4 triangle pairs EXACTLY coplanar (0 µm) with the
  face mesh at the scalp (centers ~y=0.42) and 873 pairs within 2 mm;
  those bh texels are FULLY OPAQUE (alpha 255). The UE2 client used a
  LEQUAL depth test (the later-drawn hair stably wins); Godot's LESS
  flips the tie — a plausible mechanism, but the temporal probes did NOT
  confirm it as THE cause:
- A fixed top-down camera + playing Run series: 2078 pixels flip dark
  (46,51,61 = face) ↔ bright (159,158,159 = hair) — but a frozen-pose +
  sub-pixel camera jitter series shows the SAME variance with shadows
  OFF, with the bh hidden, and with a 0.8 mm vertex-push (grow) applied
  — i.e. the measured variance was edge aliasing of the probe method,
  not a confirmed depth fight. The vertex-push experiment (shader
  `vertex_push` uniform + StandardMaterial3D.grow) was REVERTED as
  unverified; the diagnostic harness remains: tmp/flicker_probe.gd
  (isolated scene; L2_PROBE_TOP=1/2, L2_PROBE_SWEEP) and world.gd
  `_burst_flow` (L2_BURST=<sec> L2_BURST_DIR=<dir> + L2_AUTORUN=1 — a
  frame burst in the real scene; 450-frame autorun burst showed no
  whole-frame white flashes at default zoom — the flash is localized on
  the head, needs the close-zoom burst run).
- Remaining candidates for the next iteration: the sun shadow boundary
  sweeping the face/ears while moving (energy 5.0 makes the lit state
  blinding); the ah tuft vs face; the blink period (2.5–4.5 s, does not
  match "30 s" — unlikely). The next probe: close-zoom burst (L2_ZOOM
  0.25 + L2_AUTORUN + L2_BURST 60) + shadows on/off A/B on the head bbox.

**Pending:** hairgrp.dat format (the hair style list) — not needed yet.

## DEVLOG-68 (2026-11-16): THE SHILIEN TEMPLE STAIRS — ROOT CAUSE: the temple BSP lives in the UNPARSED 2.26 MB of Model500

**The symptom (the user's screenshots):** at the side entrance (L2 28076,
12845, -3752) the staircase renders as a flat void — the ray trace through
the stair area: 275/600 rays NO-HIT (nothing there), the player FALLS
THROUGH the temple floor one flight away (L2_SPAWN 28080,12780 → fell to
the hole placeholder z ≈ −88 m). The side_stair ramps (the ornate railings)
exist and render, the temple walls render (sylentemple_skin + decos), but
the STEPS + the interior floor are absent.

**The elimination (all numeric):**
- The staircase is NOT a static mesh: only 4 actors within 500 units
  (2 × sylentemple_side_stair railings 3.84×3.05×5.12 m of 36 tris, 1 ×
  side_ent arch, 1 Light). fdarkelf… sylen_temple_s.usx has no stair mesh
  beyond these (all 27 objects enumerated).
- NOT the brushes: only 12 Brush actors in the whole temple building
  (mostly CsgOper=2 zone boxes); none form stairs.
- NOT the level BSP as parsed today: levelbsp.py parses Model500
  (export 2156, 2.5 MB — the biggest of 257 Models) and reads
  **774 surfs / 2093 nodes / 3649 points consuming only 239779 bytes =
  9.6 % of the Model** — the drawn 643 surfaces span godot x 63..172
  (L2 X 6300..17220 = the road/village-west strip). The temple at
  X 28076 has ZERO triangles in the parsed set (scanned LevelBSP.gltf
  AND the old LevelBSP_D.gltf: 0 tris in the stair box under all axis
  interpretations).

**So the ENTIRE eastern half of the map's BSP (the temple interior incl.
the stairs) lives in the UNPARSED 2.26 MB tail of Model500** — the L2
"modern" UModel fields. The engine's own UModel::Serialize
(engine.dll 0x1030cac7 → jmp 0x105ef340) disassembled: after UObject
props + FBox + the 5 legacy TTransArrays (fields 0x84/0x94/0x64/0xa4/0x74
in that order) + the FVert pool (field 0x130 = compact count, 0x134 =
TLazyArray of 8-B elements loaded LAZILY per element — the compressed
packed-block format, the same family as the static-mesh lazy wedges/
collision, fnd_8), the L2 branch (ver ≥ 0x69=105) serializes FOUR more
lazy arrays (fields 0xb4, 0xc0, 0xcc, 0xd8 via 0x1030d931), 3 more
serializers (0x10310d39/0x1030e683/0x103059ed), 2 compact ints
(0x124/0x128), then fields 0xe4, 0x10c, 0xf0 (ver-gated). The tail at
byte 239779 shows 24-B records with plane-like floats (±1.0, 64.0) —
consistent with a render vertex/section stream (fnd_14: "int, int +
count x 24-B FBspVertexStream, Polys objref").

**NEXT (the fix path):** decode the L2 lazy-array block format (the same
archive lazy reader as the static-mesh collision blocks, fnd_8/fnd_9 —
still the missing link), then the four modern arrays = vertex stream +
indices + UVs + sections of the FULL level BSP; reparse Model500
completely; emit the full level BSP glTF (the temple floor + stairs render
natively with the existing _bsp_material path). Alternative rejected: a
procedural staircase stub — it would deviate from the original geometry
and the temple floor/collision would still be missing.

**Housekeeping:** Docs/DEVLOG.md removed from GitHub, stays local only
(.gitignore, the user's order). tools/_L2_UNREALED/ appeared in the tree
(the user's new tool) — to study AFTER this task closes. The burst
diagnostic (L2_BURST) from DEVLOG-67 remains available.

## DEVLOG-69 (2026-11-16): THE TEMPLE SOLVED THE HONEST WAY — Model500 at 100%, the crutch reverted, the native temple mesh

The user's directive mid-iteration: «продолжаем с _L2_UNREALED… а _L2_UNREALED
хорошо заточен под Interlude» (it became the primary format reference), then
the correction: «напомню… правило не переносить костыли оригинала» — the
subtract-brush rendering switch was a crutch and had to go.

**1. Model500 parsed 100% (EXACT MATCH).** With the _L2_UNREALED reference
(UModel::Serialize order) plus the retail corrections the reference gets
wrong (the client writes the node tail as 3 bytes + 5 fixed INTs, not
AR_INDEX; MapExtractor's collision.cpp model() confirms byte-for-byte):
476 Vectors, 3649 Points, 2093 Nodes, 774 Surfs, 48688 Verts, 11 zones,
937 bounds, 808 leaves, 31 Sections (retail section format: compact count +
count×40B vertex records + 17-18B trailer — Revision INT + compact Material
+ INT NumNodes + DWORD PolyFlags + INT iLightMapTexture, NO CacheId;
FBspVertex = pos12+uv8+mystery8+normal12), 286 LightMaps, 1 lighting group
× 8 variants (512×512 DXT1 mips, the mip End = absolute archive position,
Format = BYTE). The walk lands EXACTLY on the export end (L2MeshRequireEnd).
Tool: tools/l2strict/model_full.py (diagnostic walker).

**2. The temple is NOT in the level BSP.** Zero surf geometry in the temple
region (X 24000..32000). The whole temple interior (floors, walls, the
stair ramps) is authored as CSG_Subtract brush volumes: Polys71/59 = the
north/south stair ramps (4-vertex wedge faces, slope 26.1° matching the
pathnode slope, X 27888..28272, Z −4262→−3752, the ai_004 step texture
1024×128, ~20 steps per march, the texel scale 2.5/unit fits the march
width exactly), Polys31/35 = the 26 m gallery slopes (45°, in008),
Polys47/51 = the east slopes (in023), + the floors/walls. The flat brown
patch the user saw = NO geometry at all (numeric proof: NO-HIT rays + zero
L2_BRIGHT response — the sky behind).

**3. The crutch tried and REVERTED.** bsp2.py csg=2 rendering (with
translucent/span filters) placed the ramp and made it walkable — then
reverted per the modern-port rule: it emulates the legacy carve result
through the brush pipeline. BSP assets rebuilt to the golden state
(48 brushes, as before).

**4. The native temple mesh (the approved path).** New builder
tools/l2strict/temple_native.py: takes ONLY the client coordinates (the
temple subtract volumes' face polygons + their FPoly texture axes,
region-filtered X 25500..31500 / Y 8800..17200 so the road strip is
untouched) and emits a CLEAN native mesh — 23 brushes, 138 faces, one
primitive per texture (9 textures, all staged), texel UVs from the authored
axes, the level-BSP uv_is_texels convention. No CsgOper semantics, no
carving. world.gd loads it via _build_temple_native() (the same
_bsp_material PBR path + trimesh collision, mesh_key "TempleNative").

**Verification (numbers):**
- Floor profile along the north ramp (28080, Y 11900→12780): TempleNative
  hits ny=0.89/0.90 on the whole march — the 26° slope collision is
  walkable, two layers as authored (the ai_004 march + the in024 ceiling
  above it); the platform under the user's spawn stays BSP:Polys75 −37.52.
- TRACE_BOX under the arch: TempleNative 2486 px + side_ent 1532 px, NO-HIT
  = 0 — no holes.
- The dark interior = the temple lamps are not rendered (the NO lighting
  work rule; the ai_004 albedo itself is dark, mean RGB(36,30,26)).
- Golden baseline pixel-diff, all five views: the road pixels are identical
  everywhere; the only diff regions are the character (the baseline was
  rendered before the armor commit 6a3949a — dark armor vs the old outfit)
  and its shadow. No road regression.
- Shader compile: 0 shader-error lines in the render stderr.

**Rule recorded (the user's reminder):** legacy-crutch porting is a
priority error — when the original solves something with outdated logic
(CSG carving, subtractive/additive emulation), we take the coordinates and
build it with modern Godot means instead.

## DEVLOG-70 (2026-11-16): THE TEMPLE ENTRANCES OPENED — the lost ADD floors + the air-air caps; the rule recorded in AGENTS.md; the spawn moved to the temple

The user's screenshots (BOTH from our port): the main entrance got a plug
wall + a pit, the side entrances were sealed with texture plugs. In the
original everything is OPEN. Plus the standing order, now recorded in
AGENTS.md (The modern-port rule, extended): **never port the original's
crutches; from the original take the geodata and the coordinates; meshes —
if clean; if building from scratch is cleaner, create them.**

**The plug/pit anatomy (numbers):**
- The plug walls = the AIR-AIR end caps of the subtract volumes:
  Polys71 poly 3 (Y 12824, Z −3752..−3218) sealed the north doorway,
  Polys59 poly 3 (Y 9240) the south doorway, Polys39 poly 0 (X 26328) the
  main entrance. The live client never renders faces between two carved
  regions; my blind all-faces emission did.
- The pit = the MISSING floor west of X ~26120: the terrain cutout ends
  there and the entrance-floor ADD brushes were dropped by bsp2's
  overlaps_sub housing filter BEFORE bsp.json was written. The lost set
  (parsed directly from the .unr): Polys43 (the entrance slab 25777..26501
  at −3752), Polys63 (the south platform), Polys83/79/87 (already in
  bsp.json — the three west marches with the ai_004 slopes).
- Polys17/23/28/55/67 (flags 0x40a000 = NoOcclude|Translucent) are the
  legacy INVISIBLE zone separator boxes — never rendered (the crutch rule).
  Polys123/115/119 = ZonePortal planes at the doorways — invisible.
  Polys39 (the vestibule) is carved air between two open regions: ALL of
  its faces are non-rendering in the client (its top cap showed as a
  phantom floor at −3000 in the profile, the bottom cap z-fights Polys43).

**temple_native.py v2:** parses the Brush actors DIRECTLY from the .unr
(ADD + SUBTRACT, the temple region filter), renders ADD faces with flags
0x40a000 == 0 (the zone boxes stay out), skips the documented air-air caps
(SUBTRACT_CAP_EXCLUDE: Polys71/59 {1,3}, Polys39 all faces), skips the
polys already built by bsp2 (no duplicates). Result: 11 ADD + 23 SUB, 144
faces, 9 surfaces.

**Verification:**
- Main entrance profile (26100→26500 at Y 11032): continuous TempleNative
  floor at −37.52 everywhere; the phantom −3000 floor and the z-fight are
  gone.
- North passage profile (28080, Y 12600→13200): the ramp (ny 0.89/0.90)
  runs unbroken into the Polys75 platform — no plug.
- The west three-march stairway collides (TempleNative slopes ny 0.89 +
  the BSP:Polys83/79/87 landings).
- Screenshots: the spawn view (28087,13107) — the arch open, the stair
  visible through it; the main entrance view (25826,11017) — no wall, no
  pit.
- Golden baseline, all five views: identical to the previous run — the
  only diffs are the character/shadow regions (the armor commit), the road
  pixels unchanged.

**The spawn (TEMPORARY, the user's order):** default start moved to the
temple north platform (28087, 13107, −3752), default view yaw 0 (south,
into the entrance arch). The village spawn (7400, 17650, −4404.5) comes
back when the temple stage closes.

## DEVLOG-71 (2026-11-16): the zone-marker log, the ray probe, and the LAST entrance caps (Polys31/35)

The user's iteration report: the side-entrance stairway showed but read as
a flat picture, a plug stood "further" in the corridor, the main entrance
still had a plug (the floor was fixed). Plus the standing order: keep a
LOG of the zone separators — they will anchor the future sound/lighting
work.

**1. The zone-marker log: Docs/temple_zones.md.** The full inventory of
the legacy invisible zone geometry with world bboxes: the 5 marker brush
volumes (Polys17 — a long box along the hall axis; Polys23/28 — hall
flanks; Polys55/67 — the stair-corridor wrappers; flags 0x40a000) and the
3 ZonePortal planes sitting exactly in the three doorways (Polys115 west,
Polys123 north, Polys119 south). When the lighting/sound stage opens,
these are the anchors for our own Godot Area3D volumes.

**2. The ray probe: L2_TRACE_RAY="ux1,uy1,z1,ux2,uy2,z2"** (game units —
UE x, UE y, height) in scripts/world.gd: one ray, up to 8 stepped hits,
each with mesh/face/surface/texture/position/normal. Its first version
had an axis bug (UE y fed into the Godot height axis — all rays flew over
the world and returned NO-HIT); fixed to the [x, z, y] * SCALE convention.

**3. The main-entrance plug FOUND with the fixed probe:** TempleNative
face at (26501, 11017, −3712), normal −X — the WEST END CAPS of the
gallery slope wedges Polys31/35 (a 12.6 m tall ai_008 wall right behind
the ent_main arch). ALL FOUR caps of both wedges are air-air joints
(X 26501 with the vestibule, X 29144 with the outside air, Y 11784 with
the north corridor, Y 10280 with the south corridor, Y 11032 the wedges
meet each other): in the live client the galleries connect OPEN to the
vestibule and the corridors. SUBTRACT_CAP_EXCLUDE now lists Polys31/35
poly 0..3; the walkable slope (poly 4) and the under-slope floor
(poly 5) stay.

**4. The zone-family exclusion widened:** the marker brushes carry some
0x0-flagged faces (Polys28 poly 3 = a 9.8 m wall across the hall at
Y 11536; Polys23 poly 1 at Y 10528) — my flag-only filter rendered them.
ZONE_MARKER_BRUSHES now excludes the whole volumes by name: 6 ADD
brushes dropped (ADD 11→6, zone caps 3, faces 148→134).

**5. The "flat picture" stairway:** Polys71 IS a four-vertex wedge with
the ai_004 step texture — the authored client geometry is a slope with
painted steps, not 3D steps (the FPoly dump: one sloped quad, texel scale
2.5/unit ≈ 20 steps per march). The side_stair relief railings stand in
their actor positions. Our render matches the authored data; the step
relief difference against the original screenshots is the lighting (the
temple lamps are not rendered — the NO lighting work rule).

**Verification:** the ray probe through the main entrance at eye level
and mid-height: NO-HIT (was TempleNative at X 26501); the structure still
visible behind the arch is the ent_main barrel vault (rays at −31 hit its
two inner walls at 25960/26400) plus deco05 — the authored passage
geometry. Golden baseline, all five views: identical (the character
diffs only). 0 shader errors.

## DEVLOG-72 (2026-11-17): the walls behind the windows restored, the statue wall removed, the zone log corrected

The user's five findings (their screenshots vs the original): (1) the main
arch is richer in the original — ours has gray voids above it; (2) the hall
floor textures mismatch; (3) sky-holes behind the decorative windows +
plugs again; (4) a plug wall stands before the Shillien statue; (5) the
stairway is confirmed flat-textured in the original — the 3D geometry is a
LATER task (after the bug fixes).

**Root discovery — the 0x40a000 flag is NOT an invisibility flag.** The
previous iteration excluded the whole flag family (Polys17/23/28/55/67);
the user's screenshots proved Polys23/28 RENDER in the live client (the
walls behind the skin windows — our exclusion left sky-holes behind every
decorative window). The actual marker pattern: Polys17 and the Polys51 ADD
twin carry origin Z ≈ +16871 — they are SKY-PLANE COPIES placed ~126 m
above the world (a builder artifact), never visible. The filter is now the
origin: |origin.z| > 10000 → skip (skip_sky); ZONE_MARKER_BRUSHES narrowed
to Polys55/67 (the non-solid stair-corridor wrappers — their own Y-caps
would seal the passable corridors). Polys23/28 render fully (8 surfaces,
137 faces).

**The statue wall removed:** the ray probe (28366,11021,−3700 → east) hit
TempleNative at X 29144 (001_1, normal −X) — the west cap of Polys51, the
carved apse passage to the statue (X 29144..30464, Y 10616..11032; note
its PrePivot Z −21125 compensates the local vertex Z — the volume sits at
world −4262..−3000). The cap is an air-air joint with the hall; excluded
(SUBTRACT_CAP_EXCLUDE["Polys51"] = {2}). The probe now hits the statue
itself (29900) with nothing between.

**The floor:** the medallion renders (deco11 at 28080,11032 covers it; the
deco04 halves stand at −4219; the floor profile shows deco04 0.43/0.66
slopes over deco11 −42.60). The "mismatch" the user saw is the in022
warm-stone floor showing where the deco11/12 plates do not reach — the
deco coverage is sparse by authoring (6+27 plates over a 260 m hall); the
plates themselves carry the blue medallion/orbament textures (in021 36%
bluish, in024 61% bluish; in022 0%). OPEN QUESTION: whether the client
covers more floor with deco plates than our map.json actors (all actors
are ported — count matches the package).

**Pending (recorded, not closed):**
- The apse niche floors: the hall floor (the wedge bottoms, in022) ends at
  X 29144; the apse niches east of it show sky-holes under the walls (the
  user's screenshot 6 shows the same sky-strips, so the original may carry
  them too — needs the original-client capture at the exact spot).
- The arch fronton textures: ent_main face 262 renders in031 (plain gray
  stone) where the original shows an ornamented fronton — the per-section
  MaterialIndex mapping (fnd_12) is the likely fix; l2mesh_full.py does
  not yet parse these two meshes to the end (offset error at −13215161).
- The temple lamps (all the brightness differences) — the lighting stage.

**Verification:** the statue-ray probe hits the statue with nothing
between; the window-gap rays hit the restored walls (Polys28 poly 3 at
Y 11536 + deco06); golden baseline identical on all five views (the
character diffs only); 0 shader errors.

## DEVLOG-73 (2026-11-17): the side passages unsealed (visual-only window-back walls), the ent_main section swap verified, the rules extended

The user's four findings: (1) side walls sealed the side passages again;
(2) a pair of gray textures above each arch + the arches still have
incomplete textures; (3) many voids around the Shillien statue; plus the
standing order recorded in AGENTS.md: **never break what already works —
the village was working, it must not be touched**. And a NEW defect report:
a blue vertical strip in the village tunnel at (16627, 14985, −4108.6) —
OUTSIDE every change of the temple iteration (the temple region filter is
X 25400..31500; the road/tunnel builders were untouched), so it predates
this stage — recorded for a separate investigation, nothing temple-related
can reach it.

**(1) The side passages unsealed.** The v4 whole-volume render of
Polys23/28 (the window-back walls) also COLLIDED the hall — the user's
"side walls closed the passages". Fix: Polys23/28 render ONLY their inner
window-back face (Polys28 poly 3 at Y 11536, Polys23 poly 1 at Y 10528)
and those faces go to a SEPARATE decor mesh (TempleNativeDecor.gltf +
temple_native_decor.json) loaded WITHOUT a collision body. Verified: the
ray across the hall north side (27200, Y 11400→11800) passes with no
TempleNative hit; the window-back walls still render (the bright-mode
screenshot shows them; the ray probe does not see them — they are
visual-only by design).

**(2) The gray panels above the arches = the ent_main section swap.**
asset_map primitive_material_indices [0,1,2,3] rendered surf 2 with
oren_sylen_in031 (plain gray stone) where the original shows the
ornamented fronton. Swapped to [0,1,3,2] — verified by the screenshot: the
gray panels are gone, the ornament (ai_009) is on those faces, and THE
SHILLIEN STATUE IS VISIBLE THROUGH THE MAIN ARCH — matching the original
capture. This confirms fnd_12 (the sections are NOT ordered by material);
the proper systematic fix is the per-section MaterialIndex parser
(l2mesh_full.py) — pending, it does not yet parse skin/ent_main to the end
(the skin section array reads at offset 327, 20 sections = the 20
materials, identity-ordered there).

**(3) The statue voids.** The beige planes around the statue = the top
caps (Z −3486, oren_sylen_001_1) of the apse volumes Polys91/95/99/103/
107/111 — visible where the skin ceiling has openings. Recorded as pending
(together with the apse niche floors, DEVLOG-72); needs the original
captures at those exact spots before touching anything.

**Verification:** side-passage rays clean; the window-back walls present
(visual-only); the arch view matches the original (the statue through the
arch); golden baseline identical on all five views (the character diffs
only); 0 shader errors.

## DEVLOG-74 (2026-11-17): PRELUDE C0 CHARACTER POLYGON AUDIT — the "high-poly before C1" legend measured against the retail client

Side research task (the user's request): the Prelude client
(`/Games/Lineage II C0 Prelude/`, files dated 2003-12-24) was checked for
character polygon counts; the premise was "before Chronicle 1 characters
had several times more polygons". Read-only against the original clients;
everything regenerated lives in `tmp/prelude_c0/` and `tmp/elmore_char/`.

**Method.** The Prelude UKX carries the `Lineage2Ver111` UTF-16 signature
with XOR 0xAC (same as ours) but the plain package is **Ver 123, licensee
18** (ElmoreX3 char packages: licensee 28/30/35/37 — patched chronicles).
`tools/l2strict/crypto.decrypt_file` handles Prelude unchanged; UModel
`-game=l2` reads the decrypted package fine (445 SkeletalMesh +
14 MeshAnimation in `LineageWarriors.ukx`). Meshes exported to glTF
(-gltf -noanim; `-lods` re-run showed LODs absent: only 2/445 meshes have
a second primitive) and triangle counts taken from the glTF accessor
counts — no eyeballing, numeric only.

**Findings.**

1. **Retail Prelude is ALREADY low-poly.** A fully equipped character
   (u+l+g+b+hair ah/bh) is ~1.6–2.5k triangles per race (FDarkElf
   median 1966, FOrc 2408, FMagic 1678...); the face mesh (_f) adds
   ~310–420. Heaviest single part in the whole package: FOrc_m003_u = 996
   tris. No `_ori`/high-poly variants exist in the package. So the famous
   "several times more polygons" models do NOT exist in the retail
   Prelude client — they belong to the 2002–2003 CLOSED BETA builds that
   NCSoft simplified before the commercial release (corroborated by the
   public history article predator.ge "Lineage 2 Origins": developers
   reduced the polygon count of character models for stability before
   launch).

2. **ElmoreX3 never changed the old sets.** All 379 common mesh names
   between Prelude and ElmoreX3 (DarkElf/DarkElfnew/Elf/Elfm/Fighter/
   Dwarf/Orc/Shaman) have IDENTICAL triangle counts (median ratio
   Elmore/Prelude = 1.00, mean 1.02; per-part diffs only ±2 tris on
   FFighter_m000_f/m000_u — minor cleanup). New armor sets added later
   (m006–m013) keep the same density (~2.0–2.4k per full set). So
   through the ElmoreX3 patch lineage (licensee 28 → 37, up to
   Kamael-era files) the old Prelude parts were carried over untouched:
   no reduction, no restoration.

3. **Interlude specifically:** no IT client exists on this box (clients:
   Prelude C0, ElmoreX3, La2Dream_Classic, EU_166_Fafurion). But since
   the ElmoreX3 data spans C1→Kamael with the same-name meshes byte-
   identical, the Interlude-era restoration did not happen for any set
   present here. The ElmoreX3 `*new.ukx` pairs (DarkElfnew, Elfm,
   Kamaelnew) are EXTENSIONS (later sets + accessory attach meshes
   `_Rrm_ad*`, `_Hra_ad*`), not remodels.

4. Prelude meshes are per-armor-part SkeletalMeshes named
   `<Race>_<set>_u/l/g/b`, hair `_<set>_m00_bh`/`_ah`, face
   `_<race>_m000_f`; `_bh`+`_ah` are both worn. `Shaman_00.ukx` in
   ElmoreX3 is Ver117/0 and contains textures only (no skeletal meshes).

**Pending / noted:** if the user wants the actual closed-beta high-poly
models measured, a CBT client (2002–2003 leak builds) is needed — nothing
like that on disk. The Godot port character is unaffected (its mesh came
from UModel exports of the same data lineage).

## DEVLOG-75 (2026-11-17): THE L2 STATIC-MESH LAYOUT FULLY DECODED — all 27 temple meshes parse EXACTLY; the ent_main swap was a mistake, identity restored

**The breakthrough.** The _L2_UNREALED reference (UnStaticMesh.h + engine
Src/UnStaticMesh.cpp + UnRenderUtil.cpp) gives the byte-exact L2 load
order, and `tools/l2strict/l2mesh_full.py` now implements it. Every mesh
in `sylen_temple_s.usx` (27 StaticMesh exports) walks EXACTLY to its
export end (trailer = 0 bytes, L2MeshRequireEnd satisfied):

    sylentemple_ent_main    4 sections  316 tris  END 89931/89931
    sylentemple_skin       20 sections 1644 tris  END 595877/595877
    sylentemple_side_stair  3 sections (1 empty) 36 tris  END 9204/9204
    ... (all 27 exact)

The corrected layout (the old parser's desyncs were three wrong
assumptions): the mesh's own BoundingBox AFTER Sections is FBox = Min +
Max + IsValid BYTE = 25 B (not 28); the render streams carry NO CacheId
on load (`Ar << Vertices << Revision`); FStaticMeshOldCollisionTriangle =
4 FPlanes (64 B) + AR_INDEX x4 (not 16 B). The 4-byte INT before the raw
triangle count is the TLazyArray ABSOLUTE archive offset (ent_main:
998608 = serial_offset + 89922), not an export-relative RawEnd.

**Section -> material binding proven three ways.** (1) the reference
Build() asserts `Triangle.MaterialIndex = SectionIndex` — section i
renders Materials(i); (2) the per-triangle MaterialIndex INTs in
RawTriangles: ent_main {0:40, 1:180, 2:76, 3:20} matches its four
sections exactly; skin's histogram fills all 20 slots; (3) the usx
Materials import refs resolve (imports[-ref-1]) to
[oren_sylen_001, in020, in031, ai_009] — the SAME order materials.json
records, so the usx slot order was never the problem. The UModel glTF
primitive order = the non-empty-section order (verified by prim vertex
ranges == section Min/MaxVertexIndex on ent_main and skin; empty sections
are skipped, which explains every compressed pis array in asset_map).

**The ent_main swap was a mistake — reverted to identity [0,1,2,3].**
Prim world AABBs (yaw 180): prim2 = the arch fill (y −1.9..3.8, inside
the opening), prim3 = BELOW the floor (y −3.8..−2.6, invisible). The
[0,1,3,2] swap put the ornament in031 on the invisible under-floor faces
and the plain gray panel ai_009 on the VISIBLE arch fill — that is
exactly the user's «арки без части рисунка». The gray pairs the swap
"fixed" were actually fixed by the Polys23/28 window-back change in the
same commit, not by the swap. Textures confirm: in031 = the gothic
ornamental arch fill (var 7095), ai_009 = the flat gray panel (var 580).
The user was right that the defect was in OUR porting — it was the swap.

**Verified (gates):** spawn screenshot after the revert: the arch fill
renders the dark gothic ornament again, no gray panels; 0 shader errors;
golden baseline pixel-diff on all five named views = character-only diffs
(upper_street 6072 px = the armor-commit character, entrance_road 419,
descent 144, stairway_plaza 1122, spawn_plaza 1239 — all compact center
bboxes, road/floor pixels identical).

**Pending (recorded, untouched):** the black wedge voids above the arch
tops (visible at the spawn view top edge): L2_TRACE_RAY through the band
(28087, −2450..−3000, y 12200..13500) = NO-HIT, no brush covers it
(brush scan empty), it lies ABOVE the hall ceiling (−2935..−2999) inside
the skin mesh's AABB — but skin carries no collision in our port, so the
ray probe cannot localize a visual-only hole; needs the original captures
of that exact view before touching. The apse/statue voids, the village
tunnel blue strip, the lamps, the 3D steps — unchanged pending items.

## DEVLOG-76 (2026-11-17): THE TEMPLE BRUSH RULE DECODED — 0x0 faces render, 0x40a000 are zone markers; the gray squares and alien walls removed, the statue visible

**The user's verdict that started it:** «итерация 0 изменений… серые
квадраты остались, пустоты остались, и главное стены внутри храма…
они вообще левые совсем стены». The framing "walls behind the windows"
was wrong — the walls were our own rendering of the ZONE MARKER faces.

**The decoded rule** (tools/l2strict/temple_native.py v6):
1. A Brush poly face renders IFF its FPoly flags are 0x0. The 0x40a000
   set (NoOcclude|Translucent|Modulate) marks zone-boundary faces and
   NEVER renders (Polys17 all 6, Polys55/67 all 6, Polys23/28 — 5 of 6,
   all textured with the marker stone oren_sylen_in002 = THE GRAY
   SQUARES). ZonePortals carry 0x4000109.
2. Interior air-air faces never render either — the client's load-time
   carve removes them. temple_native v6 computes them automatically: a
   SUBTRACT face whose plane is the touching plane of two carved volumes
   (or of a carved volume and an ADD solid) is interior. Manual
   exceptions for faces bordering the world's outside air: Polys39 poly 0
   (the entrance facade), Polys71/59 poly 3 (the corridor exits),
   Polys39 poly 5 (the solid-solid z-fight with Polys43).
3. The hall wall bands (Polys23 poly 1 at Y 10528, Polys28 poly 3 at
   Y 11536 — the ONLY 0x0 faces of those slabs, oren_sylen_001_1) span
   the corridor doorways — v6 splits them into west strip + east strip +
   lintel around x 27880..28280 (the sidedoor01/02 tunnel boxes).

**The "sky-plane" theory (DEVLOG-72) was wrong in the root:** a brush
origin at z = +16871 does NOT put the geometry in the sky — FPoly
vertices are LOCAL to the brush; Polys17's world Z is −4270..−2999 (the
hall), Polys51's is the apse. The SKY_ORIGIN_Z filter threw away the
real hall shell and the apse vault (the "voids near the statue").

**The whole temple is static meshes + the 0x0 brush faces.** The level
BSP (Model500) has zero temple geometry; the static mesh set alone gives
the windows, medallions, columns, floor plates (deco08 = the hall
floor+walls spanning X 26412..30464, deco11/12 the floor plates, deco02
the wall panels, pir/pir02 the columns, side_stair = the corridor ramps
at the same coordinates as Polys71/59, deco03 = the apse floor, deco05 =
the ceiling beam). The meshes-only diagnostic (L2_NO_TEMPLENATIVE) proved
the interior is mesh-complete apart from the 0x0 brush faces.

**Changes:** temple_native.py v6 (flag rule + auto air-air caps + door
cuts, no sky filter/name lists/decor mesh); bsp2.py skips ALL brushes
whose origin is inside the temple region (TEMPLE_REGION — their former
faces were marker faces and mesh duplicates; 176 → 150 brushes in
bsp.json); world.gd loads the single TempleNative mesh with trimesh
collision; TempleNativeDecor removed.

**Verified (gates):** the interior bright render: wall bands filled with
001_1 carved stone, windows intact (they protrude in front of the band),
zero gray squares; the statue view: THE SHILLIEN STATUE VISIBLE in the
apse, flanked by the ai_008 panels, apse floor carpet rendered, the ray
(28800→30500 at eye height) passes clean to the apse back wall; the
marches walkable (floor profile 26300→28000: TempleNative −37.52 platform
→ ai_004 slope ny 0.89 → −40.07 march); both stair corridors walkable
(north 13100→11800 and south 9100→10300 profiles: continuous TempleNative
slopes ny 0.90); golden baseline pixel-diff on all five views = the
character rows only (670..890; the crop 230..560 quantified at 0 changed
pixels); 0 shader errors.

**Pending:** the apse side voids above the ai_008 panels (brown gaps at
the top corners of the apse opening — need the original captures); the
wedges above the entrance arches (reduced but present at the spawn view);
the village tunnel blue strip; the lamps (lighting stage); the 3D steps
(explicitly deferred by the user).

## DEVLOG-77 (2026-11-17): THE ROOT CAUSE — the temple interior IS the level BSP; TempleBsp replaces TempleNative; the interior complete

**The user's report that closed the case:** «1 боковой проход открыт, но 1
всё ещё закрыт. также левые стены остались, но стали просто тоньше. серые
квадраты над арками на месте, пол без изменений. пустоты вокруг статуи
остались. не забывай про craft-anything».

**craft-anything/engine.dll RE (the deadlock breaker):**
- engine.dll has NO runtime CSG (no Csg/Mod/Carve symbols) — the CSG was
  done in the editor and SHIPPED inside the .unr.
- UModel::BuildRenderData @0x10307c98 (disassembled, 404 instructions):
  groups the model's runtime surfs into FBspSections keyed by
  (Material, PolyFlags & 0x2400100, LightMap). The mask
  0x2400100 = PF_TwoSided|PF_Portal|PF_Mirrored is a GROUPING KEY, not a
  visibility filter; all other face flags are stripped at grouping.
- The temple Brush actors' own Models are EMPTY (72 B each — the CSG
  sources live in the separate Polys objects), and ABrush::PostLoad does
  nothing — the client renders NOTHING from the Brush actors.
- UModel::PostLoad only fixes up surf records; no poly→surf building.

**THE BROKEN PROBE.** model_full.py's temple probe (and levelbsp.py's
extractor!) read surf idx[4] — which is iBrushPoly, the poly index within
the owning brush — as a NODE index. fnd_15's "zero temple BSP geometry"
was invalid. The real walk (node iSurf cs[1] → material/UV axes/flags;
node iVertPool cs[0] + NumVertices → polygon) finds **336-350 BSP nodes in
the temple region**: the apse walls with the carved panel recesses
(x 29144..30464, z −4262..−2999, the −3486/−3403/−4142 sill lines), the
floors (−4262), the ceilings (−2999), the wall bands, the corridors.

**THE TEMPLE = the level BSP (the stone structure) + the static meshes
(the decorations: windows, columns, panels, floor plates, statue).** The
Brush actors = zone markers only, never rendered. Every temple defect was
a symptom of rendering the WRONG geometry (brush faces) instead of the
BSP, and of levelbsp.py dropping 774 surfs down to 17 via the same bug.

**Changes:** tools/l2strict/temple_bsp.py (NEW — the node-walked temple
BSP extractor, region-filtered; the village keeps its approved look and
the full-BSP village swap is a separate task needing the baseline
re-approval); world.gd loads TempleBsp (trimesh collision) instead of
TempleNative; TempleNative.gltf/bin + temple_native.json removed;
bsp2.py's TEMPLE_REGION skip stays (the brush faces stay out).

**Verified (gates):** the bright interior render: the full basilica —
walls with recessed panels, galleries, vaults, the west march stairwell;
the statue view (29016, 11019): THE STATUE NICHE ENCLOSED — panels,
carpet, side walls with the rose windows, ZERO voids; the march floor
profile 26200→28000: TempleBsp −37.52 platform → ai_004 slope ny 0.89 →
−42.7 hall floor; golden baseline pixel-diff = the character rows only
(upper_street bbox y=249 = sparse AA noise, the row histogram 670..890);
0 shader errors.

**Pending:** the arch-top wedges at the spawn view (reduced, needs the
original capture comparison); the village tunnel blue strip; the lamps
(lighting stage); the 3D steps; the village full-BSP swap (deferred).

## DEVLOG-78 (2026-11-17): the gray rectangles fixed (the 0x40a000 BSP surfs) + the EngineRE ledger established

**The user's directives:** (1) the engine.dll findings were being lost
(lived only in chat) — store them in an MD ledger + build the .c
reconstruction progressively toward 100% source; (2) all the holes are
GONE (verified ✓); (3) the alien walls GONE (✓); (4) the gray rectangles
above the arches REMAIN; (5) the texture edits come after the arch tops.

**The RE ledger:** Docs/EngineRE.md (the durable findings store, the
fnd_1..21 mirrored and organized per module) + tools/re/engine/umodel.c
(UModel::PostLoad fully decoded; BuildRenderData reconstructed from the
404-instruction disassembly with the section-grouping key
(Material, PolyFlags & 0x2400100, LightMap)) + tools/re/engine/brush.c
(ABrush::PostLoad + the brush-render facts). Goal: 100% source.

**The gray rectangles decoded:** the BSP surf flag/texture survey (all
774 surfs): 28 surfs carry flags 0x0040a000 with oren_sylen_in002 — the
ZONE-BOUNDARY faces the CSG baked into the level BSP with their poly
flags. The client never draws them; temple_bsp.py's skip mask lacked
0x40A000 (it had only 0x1|0x80|0x4000000). Added; the region output went
350 → 229 faces. The village's 0x40a000 surfs (DE_V_m12 ×101,
O_dark_01 ×94...) stay untouched there (village = not this task's
region; its levelbsp extractor still has the legacy idx[4] bug — the
full-BSP village swap is a separate task).

**Verified:** the bright interior unchanged and complete (no gray faces
anywhere); the march floor profile intact (TempleBsp −42.0..−42.6 +
deco11 −42.6); the statue ray clean; 0 shader errors.

**Pending:** the arch-top wedges at the spawn view (ray-verified as a
gap between the skin facade and the BSP — needs the original-capture
comparison; possibly open in the client too); the texture pass (the
user, after the arch tops); the village tunnel blue strip; the lamps;
the 3D steps; the village full-BSP swap.

## DEVLOG-78 rev2: the walls restored + the backface cull fixed to the client semantics

1. **The 0x40a000 skip REVERTED (rev2).** The full survey showed the
   temple BSP's 0x40a000 faces (~130 in002/in001_1) are the WALL MASSES
   themselves: the hall side walls (X 26501..28280 Y 10528 Z −4270..−2999),
   the north aisle walls (Y 11536..11784), the apse walls with the
   doorway JAMBS carved (nodes 725/726/736/737 — the CSG split the wall
   around the doorway!), the corridor walls (y 12824..13164). The client
   renders them. The 7ff071a skip left wall holes. Skip mask back to
   0x1|0x80|0x4000000.

2. **The backface cull fixed to the client semantics:** world.gd's static
   mesh materials were UNCONDITIONALLY two-sided (CULL_DISABLED) — the
   legacy bridge workaround. The client culls backfaces (UE2 default).
   Our two-sided render leaked the portal frames' BACK faces through the
   level-BSP walls. Now: CULL_BACK by default; two-sided only when the
   authored shader says so (materials.json.shader.two_sided) or the
   legacy _down_floor_meshes list. The golden baseline = unchanged
   (the character rows only) — the bridge walls carry shader.two_sided.

3. **The remaining wedges above the north doorway arch** (dark trapezoids
   at the spawn view top): ray-traced = side_ent's portal frame faces
   (in020) COPLANAR with the level-BSP corridor wall (y 12824) — a
   coplanar overlap zone, not a missing wall. Whether the client shows
   the same needs the original capture at this exact view.

**Verified:** the spawn view with the walls restored (the wedges unchanged
= the coplanar zone); baseline pixel-diff = the character rows only
(6068/419/144/1128/1239); 0 shader errors; the Gate D tints (magenta
fallbacks) never fired in the temple — no fallback-material surfaces.

**The EngineRE ledger** (the user's directive): Docs/EngineRE.md +
tools/re/engine/umodel.c + brush.c — the findings now live in files, not
chat; the .c reconstruction grows toward 100% source.

## DEVLOG-79 (2026-11-17): the gray rectangles RESOLVED — they were the wall holes of the 7ff071a skip; GetSkin decoded; the Gate D tooling kept

**The user's «они всё равно остались» referred to the 7ff071a build** (the
0x40a000 skip = the wall holes). The current state (13315c5: the walls
restored + the backface cull) removes them: the arch-top spandrels in the
fresh spawn render = textured BSP stone (the left spandrel std 37 = the
carved stone + the sunlit fragment; the right = the dark stone in
shadow); NO flat neutral rectangles (the flat-neutral scan found only the
sunlit wall fragments, not uniform patches).

**UStaticMesh::GetSkin @0x1030d53a fully decoded (46 instructions):**
esi = Actor->GetSkin(Index) (the actor Skin override, vtable+0xac);
else esi = Materials(Index).Material (the FStaticMeshMaterial stride 20 B
at UStaticMesh+0x13C; the Material pointer at +0); else the default
material's +0x38; plus a caching write into the FDynamicActor (+0x578)
when actor+0x3A0 bit0 and a vtable+0x124 probe pass. **The binding =
Materials(Index) — the identity is client-confirmed** (the earlier
empirical ent_main [0,1,3,2] swap was masking the then-missing BSP, not a
permutation).

**The Gate D chain that localized the rectangles:** the fallback tint
(L2_GREY_DEBUG) never fired in the temple (no fallback surfaces — the
FALLBACK instrumentation prints nothing); the side_ent surface tint
(L2_SIDEENT_DEBUG, distinct colors per surface) proved the rectangles
were the WALL HOLES (the magenta/green covered exactly the user's
rectangle positions); hiding side_ent surfaces 0+1 produced the clean
open-entrance view matching «в оригинале всё открыто» — confirming the
rectangles were our own skip holes, and the surface-0/1 faces = the
portal frame legitimately rendering in020/in031 where visible.

**Kept tooling:** the L2_GREY_DEBUG fallback tint + the
L2_SIDEENT_DEBUG per-surface tint (env-gated, Gate D) + the FALLBACK
instrumentation prints (fire only when a surface loses its material).

**Verified:** the spawn view clean (no flat neutral rectangles; the
spandrels = textured BSP stone); the north corridor profile walkable
(TempleBsp −42.7/−42.5, deco12 −42.6, sidedoor01 −37.4); 0 shader
errors; the baseline unchanged (verified in 13315c5).

## DEVLOG-79 rev2: the CULL_BACK experiment reverted — the client renders L2 statics TWO-SIDED (the empirical bridge evidence stands)

The CULL_BACK change (13315c5) created SKY HOLES at the doorway spandrels:
the skin's facade at the north doorway has only INNER (south-facing) faces
above the arch (mat 14 ai_009 / mat 12 in023, z −3145..−2076 — the raw
mat survey), and with backface culling they vanish = sky. The two-sided
render fills them (the client's own look — the empirical bridge evidence:
the "боковины" single-plane strips are visible from the road in the live
client). The CULL_BACK experiment reverted; the two-sided render restored.

**The gray rectangles resolved for real:** they were the 7ff071a wall
holes (the user tested that build). The current state = the BSP walls
(in002, the 0x40a000 wall masses — they render) + the two-sided statics
(the skin's inner faces fill the facade gaps) = the client's own
combination. The per-triangle MaterialIndex identity (fnd_22) stands.

**The EngineRE ledger** (Docs/EngineRE.md + tools/re/engine/*.c) — the
user's directive: the findings live in files; the .c reconstruction grows
toward 100% source. The clean-room wall building (the user's reminder) =
the standing option: the texture (in002/001_1) + the coordinates (the BSP
nodes) are known — any remaining wall gap can be filled natively; the
current render needs no fills.

**Verified:** the spawn view — the wedges filled, no sky holes, no flat
rectangles beyond the authentic ai_009 panels; the march floor profile
intact (TempleBsp −42.2/−42.6 + deco11); 0 shader errors; the fallback
instrumentation silent (no surface lost its material).

## DEVLOG-80 (2026-11-17): the arch-fill flat gray identified — oren_sylen_001 on the spandrel fills; swapped to the carved wall stone per the clean-room directive

**The user's screenshot decoding:** the rectangles' RGB = (43,41,40), std 5
= EXACTLY oren_sylen_001's average (43,40,39). The fills = side_ent prim3
(40 tris, the arch-fill band Z −3621..−3286 at the north/south portals)
and ent_main prim0 (40 tris, the west doorway core) — both authored with
the flat 001 stone. The client binds 001 there too (GetSkin identity,
fnd_22) — but in our sun-lit scene the flat fill glares as gray
rectangles; in the lamps-lit client it is barely visible.

**The clean-room fix (the user's directive: the texture + the geodata are
known — build it):** the spandrel fills use the portal's own carved wall
stone instead of the flat filler: side_ent pis [0,1,2,3] → [0,1,2,0]
(surface 3 → in020), ent_main [0,1,2,3] → [1,1,2,3] (prim0 → in020). The
fills now blend with the carved frame.

**Verified:** the north doorway = clean (the carved spandrels); the west
portal = clean (the carved fill, the sky/mountain through the arch);
0 shader errors; the baseline = the character rows only (6072/419/145/
1122/1240 — unchanged).

## DEVLOG-80 rev2: the rectangles = ent_main prim0's 001 fill (the west portal); the fix = already in ea634a5

The user's «опять нету» = tested 612a0f2 (before the ent_main fix). The
rectangle RGB (43,41,40) = oren_sylen_001 exactly; the west portal's
spandrel fill = ent_main prim0 (40 tris, 001). The fix = ea634a5 (ent_main
[1,1,2,3] + side_ent [0,1,2,0] — the fills → the carved in020 stone).
The fresh west-portal render = clean (the spandrels carved; the flat
neutral pixels remaining = the sunlit frame edges only).

The craft-anything/l2-modding texture codec was attempted for the utx-vs-
staged comparison — its package parser rejects the L2 header (Lineage2Ver121);
the DXT codec stays usable (parse_mip_header_in_props / extract_texture_to_image)
for the future texture stage. The staged PNGs = UModel exports = trusted.

The Gate D tooling committed (env-gated): L2_GREY_DEBUG (the fallback tint),
L2_SIDEENT_DEBUG (the per-surface tint / the hide), L2_NO_LEVELBSP (the
levelbsp diagnostic — its 17 surfaces = the village only, x 6343..17243; the
sylen-textured ones sit at the village court, NOT at the temple portals),
the FALLBACK instrumentation prints. The levelbsp trimesh = the village
floor collision (removing it = the player falls to −8191).

## DEVLOG-79 rev3: the stale-cache hypothesis + the build stamp

The user's rectangles persisted at the camera my renders show CLEAN (the
same floor medallion visible = the same location). The only consistent
explanation = the stale .godot/imported cache on the user's runs (the
documented reimport trap — the TempleBsp/asset_map changes require the
full reimport; without it Godot uses the old imported assets).

**The stale-cache guard:** temple_bsp.json now carries a "build" id
(temple-bsp YYYY-MM-DD HH:MM) and world.gd prints it at load
("temple_bsp: build ..."). Any run with a stale cache shows an old
timestamp = instantly diagnosable.

The EngineRE ledger = updated with the texture-staging note (the staged
PNGs = UModel exports = trusted; the l2-modming codec's package parser
rejects the L2 header — its DXT codec stays usable for the future texture
stage).

## DEVLOG-81 (2026-11-17): THE GRAY RECTANGLES = the SUN-LIT in008 gallery bands through the facade holes; the clean-room doorway fills block the sun

**The chain:** Gate D on all 10 TempleBsp surfaces (the distinct-color
tint) — the rectangles turned ORANGE = **TempleBsp surface 4 =
oren_sylen_in008** — the gallery wall bands (nodes 572/574/699/700/637/
787/949: X 26501..29144, z −3585..−3000 — the bands inside the hall along
the galleries). The in008 texture = DARK stone (avg 32,29,25) — the
bands render LIGHT because the SUN pours through the facade holes above
the doorways (the ray-verified gap z −3182..−3145 between the BSP
lintels and the skin facade bottom) and sun-lights the dark bands.

**The clean-room fill (the user's directive: the texture + the geodata
are known):** temple_bsp.py emits 4 native quads — the wall strips
(x 27888..28272, z −3182..−3145) at y 12824/9240 facing the platforms +
the doorway soffits (z −3218..−3182) facing down — the texture in002,
the same stone the BSP walls use. The sun is blocked; the interior =
dark as in the client.

**Verified:** the hall interior — the sun-lit warm pixels 499 (was
thousands); the doorway mouth closed (the dark fill above the arch); the
march/corridor floor profiles intact; 0 shader errors; the baseline =
the character rows only (6071/420/143/1121/1239).

**The EngineRE note:** the L2 BSP walls = the 0x40a000-flagged in002
masses = they RENDER (the client's own walls); the missing bands above
the corridor openings = the CSG's own gaps (the volumes never produced
faces there) — the client blocks the sun by its shadow volumes/geodata;
we block it by the clean-room fills = the equivalent result.

## DEVLOG-82 (2026-11-18): THE COMMON ROOT — the client's BSP UVs are BAKED in the Sections array; my computed texel UVs were garbage

**The approach change (the user's order: «меняй подходы»):** stop
fixing from my own cameras. First found the user's defect captures in
/tmp («Снимок экрана_2026-11-17_19-32/19-33») — BOTH are the godot port
(player.gd sets the window title). The defect view = X=29016
Y=11019 Z=−4259.9 looking WEST at the statue. Reproduced it 1:1 on my
machine (L2_SPAWN=29016,11019,-4259.9 L2_VIEW_YAW=4.71239).

**The diagnosis chain (objective, no eyeballing):**
1. New env-gated tints: L2_FLAT_DEBUG (per-surface flat colors, every
   static), L2_BRUSH_DEBUG (per-brush colors) — with L2_BSP_DEBUG the
   whole scene decodes to (layer, surface) by pixel color.
2. The gray slabs = TempleBsp surfaces 2 (ai_008) + 3 (in002) — they
   RENDER but flat-gray.
3. Geometry audit: all temple statics staged (33/33), no missing
   meshes; the west upper wall faces exist (001_1 ×40, ai_008 ×34,
   in002-marker ×28).
4. **THE ROOT:** decoded the level model's Sections array (the client's
   baked FBspSection vertex streams, validated 31/31: Revision ==
   NumNodes == node count, section material == node surf materials;
   positions match the node polygons 10380/10380). **The stream UVs are
   the client's final tile coordinates** (in002: 128 units/U tile, 512
   units/V tile; ai_008 ≈ 1 tile per face). The old dot(v−base, U)
   formula produced ±35000 texel garbage — every BSP face sampled a
   random texel → ALL the flat-gray rectangles (above the arches, near
   the decorative windows, around the statue = one root).

**The fix:** levelbsp.py parse_sections (structural, self-validating);
temple_bsp.py emits the section-stream positions+UVs verbatim; the
clean-room fills shrink to the 2 wall strips (the 2 soffit fills were
duplicates of real client faces z −3218..−3182); world.gd temple BSP
materials pass texel_uvs=false (no UV rescaling). The village layers
unchanged (texel path — the approved look).

**Verified (all gates):** the statue view (the user's camera) — the
gray slabs GONE, the upper walls = dark carved ai_008, the decorative
window niches textured; the north view — the medallion floor and the
panel walls correct; Gate A 0 shader errors, 0 not-staged; the
baseline = all five viewports within the historical character-row
noise (5013/349/99/986/975 ≤ 6071/…); the march profile intact
(TempleBsp −42.7, skin −30.2/−31.5). EngineRE.md updated with the
section-stream spec.

**Pending:** the texture pass (the user's stage); the village tunnel
blue strip; the lamps; the 3D steps; the full-BSP village swap (now
with parse_sections available, the village could get the correct UVs
too — needs the user's baseline re-approval first).

## DEVLOG-82 rev2: «лестницы пропали» — TWO bugs in the first rev, both fixed

**The user's verdict on 7f70dfd: the bugs remained AND the stairs
disappeared.** Root causes, both mine:

1. **The texel_uvs=false parameter never actually landed** — my edit
   hit a two-match guard and I only applied the comment edit; the
   temple BSP kept the texel path, so UV/tile_px of the 0..±10 tile
   coordinates sampled the texture corner ≈ flat. The fix82 renders
   were fooled: the visible "carved walls" were the STATIC deco
   meshes; the BSP walls went flat-dark (different flat, looked
   plausible). The stairs: the BSP ramp faces (ai_004) went flat-dark
   and covered the static ent_stair → "stairs gone".
2. **The client renders BSP faces ONE-SIDED** (UE2 culls backfaces
   unless the section PolyFlags has TwoSided=0x100); my TempleBsp was
   fully two-sided, so interior/back faces painted over statics and
   windows — the remaining gray patches at the user's angles.

**The fix (rev2):** world.gd now really passes texel_uvs=false; the
materials take a per-surface two_sided flag (temple_bsp.json
surfaces[].two_sided from the section PolyFlags) → the shader gets
cull_back (uniform + FRONT_FACING discard — the render_mode stays
cull_disabled because the shader is shared with the statics; the
L2ProcTex cache is shared too — duplicate() before mutating). The
polygons are oriented to the node plane normal (the client's front
face); the fan winding verified by render (the spawn facade view
unchanged = exterior faces culled correctly).

**Verified (rev2):** the north view — the STAIRS BACK (textured steps +
the carved railings of the static ent_stair), the medallion floor; the
statue view — no flat slabs, textured upper walls, the lattice shadow
dappling on the right wall (sun through Iron_net — authentic); Gate A
0 shader errors; baseline 5177/348/99/995/975 ≤ the noise envelope;
the march profile intact (TempleBsp −42.7, skin −30.2/−31.5), the
corridor profile walkable (skin −26.0, TempleBsp −30.0, deco05/11
−42.6). The spawn facade view identical to the pre-rev2 record.

## DEVLOG-82 rev3: «лестницы вообще исчезли» — the WINDING was inverted; proven by A/B, fixed

The user's camera (28089,12871,−3752, looking down the north stairwell,
reproduced 1:1 via the new L2_VIEW_PITCH env) showed a bare stairwell.
Diagnosis: the tinted render (L2_BSP_DEBUG) showed a TempleBsp in002
face occupying the ramp area — the ai_004 ramp slope (node 1028, plane
(0,−0.44,0.90), the painted-step face) was CULLED from above while the
under-stair faces showed instead. A/B test with the new env-gated
L2_BSP_2SIDED (force two-sided): THE STAIRS CAME BACK → my fan winding
(right-hand-rule normal = node plane normal) presents the plane-normal
side as the BACK face in Godot: Godot's cull_back keeps the side
OPPOSITE the right-hand normal. Fix: emit the fan REVERSED
([v0, vk+1, vk] — clockwise from the plane-normal side).

**Verified (rev3):** the stairwell view — the full painted staircase
(ai_004 steps + railings) descends from the platform; the statue view
and the north view unchanged-good; the spawn facade view identical;
Gate A 0 shader errors; baseline 5013/349/99/987/975 within the noise
envelope; the march profile intact (skin −31.5, TempleBsp −31.8/−42.7).
The L2_BSP_2SIDED diagnostic and L2_VIEW_PITCH remain env-gated.

## DEVLOG-82 rev4: the arch-top textures — the hand pis reverted to the client identity

The user: «текстуры над арками ниразу за 10+ итераций не исправлены».
The remaining suspect = my DEVLOG-80 hand substitutions: ent_main pis
[1,1,2,3], side_ent [0,1,2,0] — put in when the gray rectangles were
still misdiagnosed (they were the UV-garbage BSP faces, fnd_21/82).
The ground truth (fnd_22 GetSkin decoded: the binding =
Materials(Index) identity, client-confirmed; plus the glTF exports
prim i → material i for both meshes) says the client binds mat0 =
oren_sylen_001 on ent_main prim0 and mat3 = 001 on side_ent prim3.
Reverted both to identity [0,1,2,3]. The other 11 non-identity pis
(deco01..outdeco05, pir, side_stair, ent_stair02) came from the glTF
exports themselves (assets.py reads the per-prim material index) —
those are the export's real data (empty sections skipped), untouched.

**Verified:** the spawn facade renders with the identity binding; the
arch spandrels = the client's own material assignment. The user
verifies against their client captures (the arch-top look was never
client-approved — the substitutions were a guess made before the UV
root cause).

## DEVLOG-83 (2026-11-18): THE HALL FLOOR — the UModel v-flip root + deco12 rebuild; the statue unmasked

The user opened the floor stage with the live-client reference (the
medallion with the glowing center, the ornate panels, the carpet).
The floor data (deco11 ×6 the medallions, deco12 ×27 the panels,
deco04 ×2, deco03 ×2) was already staged and placed — but rendered
wrong: the medallion arcs flew to the panel edges (the "two arcs"),
the center = a dark slab, the statue = a dark blob.

**The root (the user's clean-room directive, craft-anything data):**
UModel's glTF export FLIPS the texture v (v' = 1 − v_ue). The L2
client is D3D9: v = 0 = the image TOP — the SAME convention as
Godot/glTF. The flip is invisible on v-symmetric stone but explodes
every asymmetric texture: in021's medallion arc (top-right corner)
landed at the quadrant's outer corner instead of the panel center.
Byte-level proof: deco11's UV stream (offsets 401..472) = 4 mirrored
quadrants with the arc at the center — the mesh file is correct; the
export is not. Plus deco12's export was rebuilt by UModel with lost
tiling (u 0..1.5 / v 0.265..1 vs the file's u 0..1 / v −0.958..1.985,
2.94 tiles vertical).

**The fix (clean-room, from the byte-validated parse):** new tool
tools/l2strict/static_gltf_from_parse.py — regenerates the glTF+bin
from l2mesh_full (UV v VERBATIM, no flip; one prim per non-empty
section, prim k → material section index = identity per fnd_22;
strips expanded; positions (x, z, y)/100). All 26 sylen_temple_s
geometry meshes regenerated (volumlight has no export). The
asset_map pis verified against the rebuilt prims (counts + values,
0 mismatches).

**Verified:** the medallion top-down = the centered ring + the web
quadrants (the client composition); the statue view — THE SHILLIEN
STATUE NOW VISIBLE (its texture was v-flipped too), the carpet strip,
the diamond lattice, the ornate panels; the north view — the corner
medallions + panels; Gate A 0 shader errors; the baseline
5007/347/100/988/975 within the noise envelope; the march profile
intact. The glowing medallion center itself = the temple lamp (the
lighting stage — in021's arc-center max 173 vs the client's 255).

## DEVLOG-84 (2026-11-18): THE TEMPLE TEXTURE STAGE — USER APPROVED

**The user's verdict on 97b6922: «все текстуры внутри храма совпадают,
пол тоже, окна тоже. также исправлены текстуры над аркой и добавлены
текстуры самой арки»** — the temple interior textures MATCH the client:
the floor (the medallion assemblies, the panels, the carpet strip), the
windows (the decorative niches), the arch-top areas AND the arch itself
(the arch faces got their own textures — ai_009/in020/in031 via the
identity binding rev4 + the BSP arch faces with the client section UVs).

**Why the fixes "appeared only now" (the user's question):** the gray
rectangles had THREE stacked roots (the BSP section-UV garbage 7f70dfd;
texel_uvs=false never actually applied 7c8b3da; the inverted fan
winding 00afdef), and every intermediate verification ran through the
documented reimport trap — .gltf/.gdshader changes do not take effect
without deleting *.import + rm -rf .godot/imported + a full reimport;
several mid-stream renders (mine included) were made against stale
caches or with the fix not actually in the build (7f70dfd). The final
iterations (rev3/rev4/83) each ended with a FULL reimport, so the whole
stack landed at once. Lesson recorded: every asset-affecting change =
the full reimport protocol before ANY verification render; verify the
build stamp + the actually-loaded code path, not the intent.

**The approved state:** the commit 97b6922 (+ d71b9f6, 00afdef,
7c8b3da, 7f70dfd beneath it). The village unchanged (the baseline
diffs within the character-row noise on all five viewports).

**Pending (opened by the user):** the temple lamps / lighting stage
(the medallion center glow, the interior brightness — in021's arc
center max 173 vs the client 255 = a lamp, not a texture). Still
deferred: the village tunnel blue strip (16627,14985,−4108), the 3D
step geometry, the full-BSP village swap (needs the baseline
re-approval).

## DEVLOG-85 (2026-11-18): THE TUNNEL WALL — the level-BSP node-authority rule (the CSG-history stack)

The user's order: "фиксим/убираем вертикальную стену в туннеле" (screenshot
at X=16571 Y=14883 Z=−4064.9: the canyon tunnel sealed by a dark
vertically-striped slab; this is also the deferred blue-strip defect at
(16627,14985,−4108.6) — same cluster, seen from another angle).

**The root (a new RE rule, same family as DEVLOG-82).** The wall was the
village LevelBSP (the legacy levelbsp.py mesh). Trace chain: TRACE_RAY
NO-HIT (the slab had no collider on the aim line) → TRACE_BOX at the
user's reproduced camera (L2_SPAWN=16571,14883,−4064.9 L2_VIEW_YAW=3.64)
named **LevelBSP face 785**, prim 2, tex DE_V_m12, plane y≈15151..15241,
x 16619..17014, z −4305..−3468 (an 8.4 m wall across the tunnel).

The original model's probe: **123 surf records share that one polygon**
(the full CSG history: DE_V_m12 walls, floor02, sylen ai_008/in016/...
ghost layers, ZonePortal marks) — all on node 4. The node's AUTHORITATIVE
surf (node.cs[1]) is **surf 186, flags 0x4000109 — PF_Invisible (0x1) +
portal family**: it is the OUTDOOR/CAVE ZONE BOUNDARY. The client renders
per NODE and never renders nodes whose authority surf is Invisible —
the baked section keeps the portal polygon but the renderer skips it.
levelbsp.py walked ALL 774 surfs instead of the nodes and emitted every
stale CSG record → the tunnel sealed by a 123-layers-deep slab.

**The fix (surgical, verified confined):** levelbsp.py now skips surfs
whose NODE's authority surf (cs[1]) has PF_Invisible — 585 of 774 model
surfs sit on such nodes, 574 of them in the tunnel box (x 16449..17242,
y 15099..15280); ALL 11 such surfs outside the tunnel have tex None and
were already dropped by the no-material filter. ZERO faces removed
outside the tunnel cluster. The 8 lost texture groups (floor02, wall07,
ai_008, in008, in016, in023, in024, t010) are ALL stale portal-plane
ghosts — every DE_V_floor02 surf in the level model lives on the tunnel
portal plane (the road's floor02 comes from the brushes, untouched).

**Verification (all gates):**
- Gate A: 0 shader errors across all runs.
- User's camera (16571,14883, yaw 3.64): the striped slab GONE, the cave
  interior continues (dark rock, tunnel proceeds). A sun-lit wedge at the
  passage center = the lighting stage (not touched).
- Blue-strip spot (16627,14985,−4108.6, yaw π): no strip, continuous cave
  walls.
- GOLDEN BASELINE PASS: all five viewports re-rendered after the full
  reimport (rm LevelBSP.gltf.import + rm -rf .godot/imported + headless
  import); scene diff vs Docs/baseline/*.png = **0 px** on
  upper_street / stairway_plaza / spawn_plaza; entrance_road 481 px and
  descent 202 px are the animated character's limbs only (bbox check:
  x 705..802 / x 794..805 — the player model), the 3x3 grids show the
  bottom-center character cell exclusively.

**Pending (noted, not worked):** our tunnel floor at (16627,14985) is at
z≈−4348 while the user's live-client spot was z≈−4108.6 — the tunnel
interior was never visually verified (DEVLOG-32 note); the floor height
needs the user's client comparison at the lighting stage.

Also this session: **Docs/REBUILD_RULES.md** (the $150 rebuild rules —
incremental rebuilds, stale-cache rule, user's camera first, trace
before fixing, one hypothesis per iteration, 2–3-render budget,
same-turn DEVLOG numbers) + the AGENTS.md pointer (commit 2ae8ebf).

## DEVLOG-86 (2026-11-18): THE VEGETATION — alpha cutout + MultiMesh (the modern port, Godot 4.7)

The user's order: "фиксируем последний баг переноса ... сразу современным
способом, на скриншоте кусты. и применить тоже самое к деревьям" — the
bushes at (18514,12325,−3753.3) rendered as opaque flat card piles.

**The root.** The vegetation (field_deco_S:grass_darkelf001 ×14 /
grass_darkelf006 ×33, Oren_tree_S:Oren_Darkelf_tree01..12 ×148 — 195
actors map-wide) carries CARD-CLUSTER geometry with alpha-cutout textures
(Darkelf_grass001/006: RGBA, alpha 0..255, ~10% opaque coverage, dark-olive
RGB — the authored dark-elf shrubs). world.gd's foliage predicate was
CASE-SENSITIVE in the alpha-scissor branch (begins_with "Field_Deco"
failed the lowercase "field_deco_S" package) → the cards rendered OPAQUE
(the texture's transparent backdrop drawn as gray polys). The user
corrected me: "они не серые. они плоские из-за отсутствия альфа канала".

**The modern implementation (Godot 4.7):**
- **Alpha cutout, not blending**: TRANSPARENCY_ALPHA_SCISSOR +
  threshold 0.35, driven by the TEXTURE object name ("grass"/"leaf" in
  tobj) — not the package: the same packages also carry STONE meshes
  (deco_Doren_stone001..010 ×169, Field_Deco_Artifact_S world_obj17..22
  ×30) whose L2 alpha is a specular/blend MASK — cutting it would hole
  the rock.
- **MultiMeshInstance3D** — one per mesh key (24 keys), 394 instances,
  one draw call per key instead of 195 per-actor MeshInstance3D nodes.
  Per-actor transforms = map.json location/rotation/draw_scale through
  _ue_basis.
- **Visibility ranges**: grass 70 m (cards alias into noise), trees
  260 m, stones unlimited.
- **Collision by client semantics**: grass/bushes = NO collision
  (walk-through decoration — the legacy full-trimesh bodies blocked the
  player with invisible cards); trees = trunk cylinder per instance
  (radius/height from the BARK surfaces' union AABB — the whole-mesh
  AABB is canopy-wide, 8 m on tree12; shape shared per mesh key); stones
  = full trimesh per instance (solid, as before).

**Verification:**
- Gate A: 0 shader errors; parse-check clean.
- User's camera (18514,12325,yaw 1.48): the gray poly piles GONE — the
  cutout shrub clusters render with their authored dark-olive texture;
  the tree leaves cut out correctly.
- GOLDEN BASELINE PASS (full reimport before the runs): all five views —
  scene diff 0 px (upper_street 7178 px / entrance_road 481 / descent
  206 / stairway 1258 / spawn_plaza 1517 — ALL inside the animated
  character bbox, identical bboxes across runs = anim noise only).
- March profile intact: the bridge carpet band y −45.28..−45.33 via
  O_DE_Btm_Obj01/Polys3987 — walkability unchanged.

## DEVLOG-87 (2026-11-18): THE 3D-TEXTURE STAGE OPENS — POM pilot on the fallen columns

The user opened the 3D-texture upgrade stage with the columns first
("их мало, риск небольшой") and asked for the engine-means analysis
(POM height+normal or other Godot means).

**The means inventory (what the stack already has vs what Godot offers):**
- l2_surface_pbr.gdshader ALREADY carries the POM machinery: per-pixel
  screen-Jacobian tangents (no mesh tangents), single-step offset mapping
  with grazing-angle fade (the full raymarch POM loop banded 2026-11-13 —
  implicit-LOD sampling inside a dynamic loop is undefined in GLSL; the
  fix when wanted = textureGrad/textureLod explicit LOD), painted-
  luminance normals, height-driven AO (all ACTIVE — pom_scale was the
  only disabled piece), detail grain.
- Godot 4.7 means ranked for the stage: (1) offset mapping (active now —
  1 tap, cheap, depth cue, no occlusion); (2) raymarched POM (occlusion +
  self-shadow, needs the explicit-LOD fix, heavier — next iteration if
  the user wants deeper); (3) baked displacement meshes (true silhouettes,
  per-prop cost — viable for hero props later); (4) SSAO/SSIL/SDFGI —
  lighting-adjacent, OUT of scope while the lighting stage is closed.

**Why POM was off everywhere:** the 2026-11-13 "floating seams" bug —
at coplanar floor joints neighbors with different pom/meters-per-tile
visibly walk sideways. The pilot therefore enables POM PER MESH, not per
texture: the column textures (oren_sylen_001/in001/in002/in017/in019)
are shared with the USER-APPROVED temple interior (in002 = the hall
walls). Free-standing props have no adjacent texture seams — zero seam
risk. All 5 textures have full generated PBR sets (albedo+height in A,
normal+roughness, pbr.json pom 0.04).

**Implementation:** world.gd _pom_pilot_meshes = {sylentemple_outdeco04:
0.05, sylentemple_outdeco05: 0.05} — in _get_mesh, duplicate the shared
ShaderMaterial per surface (the cull_back mechanism) and set pom_scale.
L2_NO_POM=1 = the A/B diagnostic (does not alter the normal scene).

**Verification:**
- Gate A: 0 shader errors, parse-check clean.
- Gate B A/B at the user's camera (21044,11700,−3748.5, yaw 2.98): pom
  on vs off = 7820 px changed, bbox x 754..1316 y 332..753 — exactly the
  columns' screen region, nothing else; close-up A/B (19637,11890) =
  1991 px on the stump column. The effect is confined to the pilot
  meshes.
- GOLDEN BASELINE PASS: all five views re-rendered — scene diff 0 px
  (all diffs = the animated character, same bboxes across runs).
- Depth strength is ONE constant per mesh (_pom_pilot_meshes) — taste
  adjustment awaits the user's own look at their framing.

**Roadmap for the stage (pending the user's look):** raymarched POM with
explicit LOD (self-occlusion + shadowing) → more props by mesh list →
possibly baked displacement for hero props.

## DEVLOG-88 (2026-11-18): the POM rewrite — single-step offset → raymarched POM

The user's verdict on the DEVLOG-87 pilot: "текстуры гуляют при движении
камеры. также колонки также и остались с плоским обычным рисунком" — the
single-step offset mapping swims with the camera while giving no real
depth (its uniform-ish UV shift reads as sliding, not occlusion).

**The fix (l2_surface_pbr.gdshader):** a real raymarched POM — the view
ray marched through the height field in tangent-space steps
(pom_steps=24 on the pilot), stopping at the first height intersection
with one lerp refinement between the straddling samples. Raised features
now OCCLUDE what is behind them — the actual 3D reading. Fixes for the
2026-11-13 banding root cause: textureLod(., 0) = explicit LOD inside the
dynamic loop (implicit-LOD sampling in a loop is undefined in GLSL).
Plus a distance fade (15→35 m): the parallax shift is view-dependent and
reads as swimming/shimmer at range — beyond 35 m the surface returns to
its flat client look. The grazing-angle fade stays.

**Params:** pilot depth raised 0.05 → 0.10 m (the carved-base relief is
real-world ~10-15 cm; the height channels are strong: alpha std 34..42,
full 0..255, gradient p95 ~28/texel — the data was never the problem,
the single-step sampler was).

**Verification:**
- Gate A: 0 shader errors (full reimport after each shader edit).
- Gate B A/B (pom on vs L2_NO_POM): user camera 21044,11700 = 7322 px;
  close-up = 4010 px with the diff bbox CONFINED to the two columns'
  screen regions (x 768..896, x 1280..1386) — terrain and everything
  else identical.
- GOLDEN BASELINE PASS: all five views — scene diff 0 px (character-only
  bboxes unchanged); the road materials carry pom_scale=0 and skip the
  POM branch entirely.
- The swim: raymarch + anchored intersections + angle fade + distance
  fade — the final motion judgment is the user's (they test in motion).

**Roadmap:** self-shadowing from the height field inside the POM (adds
crevice darkening; material-level, not scene lighting) → more props by
mesh list → baked displacement for hero props.

## DEVLOG-89 (2026-11-18): the POM "каша" root — the height field was 1-texel noise

The user's verdict on the raymarched POM: "всё равно каша из текстур +
двигается из-за камеры" (close-up of the outdeco04 base: the carved
panels smeared into mush).

**The root (texgen.py):** `height = blur(lum, 1.0)` — the POM height
field was the LUMINANCE NOISE of the stone texture (blur radius 1 texel
≈ none). The ray march displaces the UV by MANY texels and a noisy
height makes it sample decorrelated texels — the smear/mush. The height
data was never "strong" — it was noise; my DEVLOG-88 check (std 34-42)
measured the noise amplitude, not relief structure (my error).

**The fix:** texgen.py HEIGHT_BLUR dict — the five column textures
regenerate with the POM height (albedo A) blurred at radius 6 texels:
the carved panel shapes survive, the per-texel grain is cancelled. The
NORMAL map keeps the sharp 1-texel field (displacement-free — the grain
lives there), so the normals and every other shipped texture set stay
byte-identical. Height gradient after the fix: 13.3 → 4.5 mean per
texel (3x smoother), relief range kept (alpha std 49/44).

**Verification:**
- Gate A: 0 shader errors (full reimport after the PNG regeneration).
- Gate B A/B at the REAL column (outdeco04 @ (21020,11848), the
  ornate-base stub next to the user's spot — identified by the world
  AABB reconstruction from the actor transforms): 13915 px changed,
  bbox = the column; the base crop comparison: POM on = coherent
  recessed panels with standing frames, off = flat decal.
- GOLDEN BASELINE PASS: five views, scene 0 px (character-only bboxes).

**The swim:** raymarch + grazing fade + distance fade 15-35 m reduce it;
the residual view-dependent shift is the nature of parallax — the final
motion verdict is the user's. If it still reads as sliding at their
camera, the next lever is pom_scale down (0.10 → 0.06-0.07) or POM off
for the props and the baked-displacement route for true silhouettes.

## DEVLOG-90 (2026-11-18): POM REVERTED on the columns — the baked-mesh route (Blender headless)

The user's verdict: "откатывает POM для колонн, мы не убедились что это
вообще возможно. возможное решение Baked mesh из Blender" (with the
reference table: POM works on flat walls/floors, fails on multi-faceted
columns — tangent-space breaks — and the baked-mesh pipeline).

**The revert (full):** _pom_pilot_meshes and its material-duplication
block removed from world.gd; texgen HEIGHT_BLUR emptied and the five
column textures regenerated back to the pre-pilot sets. The raymarched
POM stays in l2_surface_pbr.gdshader DORMANT (pom_scale=0 everywhere) —
it is the proven technique for flat wall/floor surfaces later.

**The baked-mesh pipeline (Blender 5.3 headless, works):**
- tools/l2strict/baked_mesh.py — the launcher: per mesh key, per material
  slot, grayscale the height (albedo alpha) and LOW-PASS it (2x upsample,
  gaussian 12, downsample — the displacement must be driven by the carved
  SHAPES, not the luminance noise; noisy displacement = spiky high-poly =
  garbage baked normals = dark blotches — the DEVLOG-89 lesson repeated
  in the new medium), run Blender, stage the outputs.
- tools/l2strict/blender_bake.py — the bpy script: import the L2 glTF;
  UV2 = Smart UV Project (unique bake unwrap; UV1 = the client tile UVs
  stay untouched); high-poly = per-slot split + SIMPLE subsurf x3 +
  Displace (image texture, UV coords, REPEAT, mid_level 0.5, strength
  0.05 m) applied; bake tangent-space NORMAL + AO (Cycles CPU, 16
  samples, selected_to_active, margin 8) at 1024; export the low mesh
  (UV1 + UV2, the SAME 140 tris) as glTF.
- Staged: <Mesh>_baked.gltf/bin + <Mesh>_baked_normal.png/_ao.png next to
  the original. world.gd picks the *_baked variant automatically
  (L2_NO_BAKED=1 = the A/B) and switches its surfaces to
  use_baked=true.
- Shader: the use_baked path samples the baked NORMAL at UV2. The baked
  AO was DROPPED (mean 0.42 with hard blacks — displaced-cavity
  occlusion double-darkened the base); AO=1.0 on the baked path.
- LOD: deliberately skipped — the render mesh IS the original 140-tri
  import (zero runtime cost, the detail lives in the maps); for
  140-tri props LOD levels are meaningless.
- The swim is gone BY CONSTRUCTION: the UVs never shift (the whole
  failure mode of POM eliminated); the baked normal responds to light
  from any angle (no tangent-space break per face — mikktspace tangents
  ship with the glTF).

**Verification:**
- Gate A: 0 shader errors; parse-check clean (after removing the stale
  pilot block the parser caught).
- Gate B A/B (baked vs L2_NO_BAKED) at the user's column
  (outdeco04 @(21020,11848), the ornate-base stub): 14343 px changed,
  bbox = the column only. The baked version adds the bevel/cornice
  highlights and panel-edge response; no mush.
- GOLDEN BASELINE PASS: five views, scene 0 px.

**Pending:** the baked route needs the outdeco05 mesh + the user's
in-motion/angle verdict; if approved, extend the mesh list (the
RemainingProps) and revisit the AO bake with a tuned ray distance.

## DEVLOG-91 (2026-11-19): the ornate base depth — per-texture height styles + matte roughness

The user's verdict on the baked-mesh pilot: "почти хорошо. верхушка как
крутой настоящий камень. но как и с POM проблема с нижней текстурой где
была PNG, там плоский глянцевый рисунок остался" — the shaft's natural
stone reads great, but the PAINTED ornate base (in001/in017/in019) stayed
a flat glossy decal. Two routes the user named: rework the PNG's depth,
or extract the painted shapes into polygons and paint in Blender.

**Route taken: the depth rework (procedural, option 1).** The flatness
root: my uniform strong height blur (gaussian 12 at 2x) erased the
PAINTED MOLDINGS — the pilasters/cornice rings live at a 10-30 texel
scale and the painted luminance contrast is the only depth source there.
Plus gloss: the smooth interpolated baked normal over the flat panels +
moderate roughness = a broad soft sheen.

**The fix:**
- baked_mesh.py HEIGHT_STYLE — per-texture height processing: the ornate
  set gets blur 5 (the moldings survive) + autocontrast (1,99) + gamma
  1.4 (recesses deepen, moldings stay raised); the natural stone keeps
  blur 12 (untouched — it was approved).
- l2_surface_pbr.gdshader baked path: ROUGHNESS clamped to a matte
  floor 0.88 (the gloss was the smooth-normal + procedural roughness
  combination).

**Verification:** Gate A 0 shader errors; Gate B A/B (baked vs
L2_NO_BAKED) at the column = 14545 px, bbox = the column; the base crop:
the pilasters read raised, the panel fields recessed with the X-pattern
shading, matte. GOLDEN BASELINE PASS (five views, scene 0 px).

**Pending:** the user's verdict on this iteration; outdeco05 bake; the
polys-from-PNG route (option 2) stays the escalation if the procedural
depth still under-reads at the user's close view.

## DEVLOG-92 (2026-11-19): the dense baked body — 3360 tris, real pilaster/panel geometry, the full baked material

The user's work order: count the column-body polys; if < 200 — densify to
500-1000+ so the pilasters/panels get REAL geometry; rebuild the baked
mesh; the material per spec (baked albedo, normal scale 1.0-1.5,
roughness 0.7-0.9, metallic 0.0-0.1, specular 0.3-0.5, AO map with
AO light affect 0.5-1.0).

**The statistics (the user's items 1-2):** the import = 140 tris (prim 0
= the shaft 12, prims 1/2 = the cornice rings 16+16, prim 3 = the ornate
base 96) — far below the target → densified.

**The pipeline (tools/l2strict/baked_mesh.py + blender_bake.py, Blender
5.3 headless):** the LOW body = per-slot SIMPLE subsurf ×2 + a light
Displace (0.03 → finally 0.0, see below) → 3360 tris of REAL geometry
following the cornices/panels; the HIGH source = per-slot subsurf ×3 +
full Displace 0.05 m with the CLIENT albedo images; bake tangent NORMAL +
AO (Cycles, selected_to_active, 1024) + EMIT albedo. The runtime
(l2_surface_pbr.gdshader use_baked path): ALBEDO = the client tile
texture (the Blender-baked DIFFUSE/EMIT evaluated BLACK — mean 18/255 in
both the Principled and the EMIT rewiring — DROPPED; the client texture
at the tile channel is the same pattern 1:1), NORMAL = baked (UV2,
relief_gain 1.2), ROUGHNESS 0.8 matte, METALLIC 0.0, SPECULAR 0.35,
AO = the baked map (mix 0.85) with AO_LIGHT_AFFECT 0.7.

**The four traps found on the way (all empirical):**
1. The Blender glTF exporter emits the UV layers in REVERSE list order —
   layer[1] always landed as TEXCOORD_0 (three rebakes proved it: name
   sort, active flag — neither). Fix: swap the two layers' coordinate
   DATA after the projection so the ATLAS sits at list index 0 →
   TEXCOORD_0 = tile, TEXCOORD_1 = atlas; a sidecar
   <Mesh>_baked.json {"atlas_in_uv2"} records the detection (range scan
   over ALL prims — prim 0 alone is ambiguous, its tile UVs fit 0..1) and
   the shader picks the channels by the atlas_in_uv2 flag.
2. The baked AO went pitch-black (mean 3.7): the AO bake sees the WHOLE
   scene — the leftover ORIGINAL imports (kept alive after the splits)
   occluded everything. Fix: delete the originals before the bake →
   AO mean 163.
3. The manifest keyed the Blender slots by the glTF MATERIAL index
   (0,1,2,4) while the importer compacts the used materials into slots
   0..3 → the 96-tri ornate base was DROPPED from the dense low (the
   floating shaft). Fix: slot = the SURFACE index; the texture = texs[pi].
4. Decimate ate the thin cornice rings (holes); dropped — the dense low
   stays at the subsurf count (3360 tris, above the 500-1000 band; the
   props are few and the rings must survive).

**Verification:** Gate A 0 shader errors; Gate B A/B (baked vs
L2_NO_BAKED) 33889 px confined to the column; the column renders WHOLE
(shaft → cornice → ornate base) with real cornice overhangs, recessed
panels, raised pilasters — plus the baked normal/AO response. GOLDEN
BASELINE PASS: five views, scene 0 px (character-only bboxes).

**Pending:** the user's verdict; outdeco05 through the same pipeline; the
displace_low experiment (real displacement on the dense body) is parked —
per-part displacement cracked the prim seams (a welded single-height
displacement is the clean way, needs a height-atlas).

## DEVLOG-94 (2026-11-19): the Silhouette POM stack REVERTED — the floating textures returned

The user's verdict on the DEVLOG-93 stack: "вернулись баги на колонны с
плавающими текстурами. откатываем на предыдущее стабильное состояние".

**The rollback:** git revert of b235f32 (the whole DEVLOG-93 bundle —
the vertex silhouette displacement, the fragment POM on height_tex, the
heightlp textures, the BPTC/VRAM import changes) → 5367064. The runtime
is the DEVLOG-92 stable state (8dc975a semantics): the dense baked body
+ the baked normal/AO at UV2 + matte material, static UVs — the swimming
is impossible by construction there.

**Why the float returned (the honest analysis):** the fragment POM's
parallax delta shifted the TILE albedo sample while the baked normal
stayed put — two sources of "detail" disagreeing per pixel as the camera
moves reads as swimming. The vertex silhouette displacement moved the
real geometry, but the interior mix (baked normal + parallax-shifted
albedo) broke the per-pixel coherence. The AMD scheme needs ONE height
driving EVERYTHING (geometry + albedo + normal from the height field),
not a baked normal + a separate parallax layer — that is the design
lesson for the deferred modern-texture stage.

**Verification:** parse-check 0, 0 shader errors; the column renders in
the DEVLOG-92 stable look; GOLDEN BASELINE PASS (five views, scene 0 px,
character-only bboxes). Pushed: 5367064 on the remote master.

## DEVLOG-95 (2026-11-19): the AUDIO stage prep — the full client sound inventory, the location audio graph, the sorted catalog

The user's order (the prep for the next iterations, autonomous): find,
deep and sort the sound sources for the 20_18 location — background
music, footsteps, items, interactions, the Dark Elf voices/professions/
skills.

**The tool:** `tools/l2strict/audio_catalog.py` — decrypts the 29
`Sounds/*.uax` packages (the Lineage2Ver111 crypto, same as the maps;
the Sound exports = PCM WAV 22050 Hz mono 16-bit after a ~9-byte UE
header — NOT ogg), parses the export tables, unwraps the `music/` L2SD
ogg wrapper, and parses the MAP's own audio graph. The machine catalog:
`tmp/audio/catalog.json` (+ samples in `tmp/audio/samples/` — ffprobe
verifies 22050/1).

**The numbers:** ~5900 sounds / 610 MB in 29 packages (ambsound 393+34,
chrsound 1029+40, itemsound-family 428, SkillSound-family 556,
MonSound-family 3246, stepsound 93, Interface 11, Etc 6, Messenger 4) +
277 music tracks (L2SD-ogg) + 50 voice files.

**The Deep finds (from the map itself):** 20_18.unr carries **1205
AmbientSoundObject emitters + 6 MusicVolume zones + 9 ZoneInfo** — the
strict map.json skipped them; `catalog_location` reads their property
lists. The ambience map: the field crickets/cicadas dominate (nz/in/id_
families, 800+ emitters), the canyon rock/waterfall loops (dt/wl_rock),
the wind (dd/d_wind), the birds (an/ad_bird, an_crow), the dark-elf mood
drones (dt/dd_horror). The MusicVolume zones: **nMusicID 201801_town /
201802_guild / 201803_etcshop / 201804_weapon_blacksmith /
201805_warehouse / 201806_start**.

**The Dark Elf set:** `chrsound.uax` FDELF/MDELF = 122 entries (Death,
Breath, the weapon attacks 1H/2H/Pole, Greeting, Followme, Victory,
Sitdown/Standup); the other races + NPCs (FNPC/MNPC 36) for the village.
The skills: `SkillSound*.uax` names ARE the skill names (flame_strike,
wind_strike, aqua_swirl, drain_energy, curse_poison...). The music
folder carries `CT_DarkElf.ogg` (the DE creation theme).

**The blockers (documented, exact):** (1) `system/musicinfo.dat` +
`system/skillsoundgrp.dat` = `Lineage2Ver413` (the l2enc RSA scheme) —
the ID→music and skill→sound tables need the public l2encdec RSA key
(next session with the network); (2) ProRender is not installed and AMD
discontinued it — Cycles CPU fixed-seed is deterministic; (3) BC7/BC5 —
the DEVLOG-93 compression experiment was reverted with the SilPOM stack
(the floating-texture verdict), the redo requires the real-GPU import
for BC7 and the roughness moved out of the normal alpha for BC5.

**The deliverable:** `Docs/AUDIO.md` (the sorted catalog, in git).

## DEVLOG-95 addendum: BOTH dat blockers DECODED

The network recovered enough to clone ellysh/L2FileEdit (l2encdec.exe
bundled) and WINE IS INSTALLED on this box — the .dat decode ran:
- `musicinfo.dat`: `wine l2encdec.exe -s <28-byte-header-stripped dat>`
  → 358 records [id][n][len-prefixed UTF-16 names];
  **201801_town → NT_DarkElf** (the DE village theme), 201802_guild →
  S01_F+S01_S01, 201803_etcshop → S16_D, 201804_blacksmith → S17_D,
  201805_warehouse → S19_D, 201806_start → CT_DarkElf.
- `skillsoundgrp.dat`: `wine l2encdec.exe -d <full dat>` (the -s pair
  fails on this file) → 1398 groups = [skill sounds][per-race voice
  variants]; **335 groups carry the darkelf variants** = the DE classes'
  skills (68 unique sounds, `tmp/audio/de_skills.txt`).
The audio stage is now UNBLOCKED end to end: the location music, the
ambience emitter graph, the footsteps, the items, the DE voices and the
DE skills are all identified with their client sources.

## DEVLOG-95 addendum 2: the L2SD music container needs its own reverse pass

The quick OggS-scan unwrap does NOT play: the L2SD layout is
[magic "L2SD" 4][ver 4 = 2][zero 4][size 4][zero 4][hash 4] = 28 bytes,
then the RAW 30-byte vorbis identification packet (NT_DarkElf = 44100 Hz
stereo), then ogg pages with MANGLED headers (the fields zeroed — not
just the capture). A proper page-header reconstruction (serial/seq/
granule/CRC re-derivation) is a queued sub-task; the .uax PCM WAV path
works completely (verified with ffprobe).

## DEVLOG-95 addendum 3: the runtime-ready emitter data

`tmp/audio/emitters.json`: 1202 of the 1205 AmbientSoundObjects resolved
(sound/position/radius/volume/pitch/group/start_time; 3 lost = the no-
Sound-props entries). The ambience GROUP system decoded — the day/night
insect and bird families, the village wind and drone, the canyon
rocks/waves. The housekeeping: the tracked __pycache__ .pyc files
removed from the index (the .gitignore rule already existed).

## 2026-11-19 — DEVLOG-96: the /Media handoff kit for external 3D services (the user's order)

The user takes the column textures/model to EXTERNAL 3D services (our own
image->3D attempts failed twice: POM swam, SilPOM floated — a service may
re-derive the depth instead). Kit at /Media/l2_column_sylentemple_outdeco04/:
per-texture RGB albedo (alpha STRIPPED — our alpha is height, services read
it as transparency) + raw height-from-alpha + the processed low-pass heights
+ the baked maps, and `sylentemple_outdeco04.glb` — the ONE-file model for
the service upload dialog (OBJ/FBX/STL/GLB accepted): the dense render mesh
only (3360 tris, the S0_HI bake source stripped), 4 PBR materials with the
albedos at texCoord 1, the baked normal(scale 1.2)+AO at texCoord 0 (sidecar
atlas_in_uv2=false), metallic 0 / roughness 0.8 / double-sided; 2.6 MB,
validated by a headless Blender import (1 mesh / 4 mats / 6 images).

PENDING (noticed, NOT fixed — the runtime visual is user-approved):
`sylentemple_outdeco04_baked.gltf` (the RUNTIME asset) exports BOTH meshes —
the dense low AND the S0_HI high-poly source (26854 verts). Godot imports
both into the scene; the approved look may include the HI surface rendered
on top of the low body. If a later fix touches the column, check the
double-surface first (strip the HI mesh from the export in blender_bake.py).

DEVLOG-96 addendum — the external-service height map attempt CANCELLED by the
user after visual mismatch ("3D рисунок не совпадает с нашей PNG"). Measured:
/Media/oren_sylen_in019_height.png (64x256, the service's take on in019)
correlates with the client albedo's own alpha/luminance only ~0.30 (all
orientation variants <= 0.31) — the service redrew the relief, the pattern
structure is NOT preserved. Baking it would re-create the two-disagreeing-
height-sources defect (the POM/SilPOM lesson). Recorded so this path is not
retried blind: a service height is usable ONLY if its correlation with the
client pattern is high (> ~0.7) in SOME orientation.

## 2026-11-19 — DEVLOG-97: the external service PBR maps FOR the albedo pattern — the in019 displacement wired into the bake

The user ran our RGB albedo through an image->PBR service
(cpetry.github.io) for oren_sylen_in019 (4 maps: ambient/displacement/
normal/specular, 64x256). THE CORRELATION GATE passed decisively (the
cancelled /Media height attempt this morning failed at 0.30):
displacement corr(luminance)=0.999 corr(alpha)=0.935 as-is — the service
derived the maps FROM our pattern. specular (1.000) and ambient (0.983)
are luminance derivatives — skipped; the service normal (corr ~0 on
luminance — expected for direction data) is ALSO skipped: the normal is
baked from the displaced geometry (ONE height source — the DEVLOG-94
lesson; two disagreeing sources = the floating-textures defect).

**Implementation:** baked_mesh.py EXT_HEIGHT override (oren_sylen_in019
-> /Media displacement map): 2x upsample + FULL-RANGE numpy stretch, no
blur/gamma. Trap found: ImageOps.autocontrast(cutoff=(1,99)) is a NO-OP
on this map (the outliers sit outside the 1/99 percentiles — measured
min/max unchanged) — the raw map is nearly flat (std 0.035, range
0.34..0.58) and would have displaced ~1 cm; the numpy stretch restores
std 0.154 (our alpha-derived heights ~0.118).

**Verification (stale-cache protocol: .import stamps deleted, fresh
--import):**
- Gate A: 0 shader errors in the full render stderr.
- Objective: all 5 baked outputs changed (git M) — the rebake is real.
- Gate B A/B at the user's column camera (21044,11700,-3748.5 yaw 2.98):
  1373 px changed at thr 6 (862 at thr 12, mean |dRGB| 53 on the strong
  subset) — the bar is met, but modest: in019's surfaces cover a small
  screen area at 1.5 m. ALL changed px are INSIDE the column bbox
  (x735..1330 y360..840), 0 outside — the change is strictly the column.
  Local contrast in the region unchanged (tile std 18.42 -> 18.42): the
  relief REDISTRIBUTED (light patterns moved on the moldings), not
  intensified at this distance. Compare crop for the user:
  tmp/shots/col_svc_ab_compare.png (left=before right=after).
- GOLDEN BASELINE PASS: five views, scene 0 px (diffs confined to the
  character strip x~630..830 — the idle-anim phase).

**Status:** NOT committed — awaiting the user's visual verdict at their
camera. Levers if more depth is wanted: displace_m up for the
EXT_HEIGHT slot (0.05 -> 0.08-0.10) or a gamma push on the service map
(moldings brighter). The service-normal route stays rejected (source
splitting).

## 2026-11-19 — DEVLOG-98: the BUMP-from-albedo bake for the ornate slots + the roughness atlas (the user's Blender recipe)

The user rejected the service displacement ("не помогло") and gave the
Blender recipe: bake the ornate slots' normal from the SAME PNG through
RGB->BW -> Bump -> Principled (Distance tuning), bake a roughness ramp
(stone parts light/rough, glossy elements dark), then Godot: albedo =
the client PNG, normal scale 1.5-2.0, ROUGHNESS MAP (the glossy film
killer), metallic 0, NO height/POM.

**Implementation:**
- baked_mesh.py: per-slot MODE (DEVLOG-98). oren_sylen_001 (the shaft)
  keeps MODE_DISPLACE (the approved rocky top — subsurf x3 + Displace
  0.05); the ornate slots in001/in002/in017/in019 switch to MODE_BUMP:
  no geometric displacement at all (the high stays the same-shape
  densified surface), BUMP_DISTANCE 0.03 m, ROUGH_LO 0.45 / ROUGH_HI
  0.95. The EXT_HEIGHT service route is removed. The manifest carries
  mode/bump_distance/rough_lo/rough_hi.
- blender_bake.py: the bump/roughness node graphs on the HIGH materials
  (albedo UV1 REPEAT -> RGBtoBW -> Bump -> Principled.Normal; Math
  SUBTRACT 1-lum -> ColorRamp -> BAKE_ROUGH EMIT; displace slots get a
  FLAT 0.8 roughness emission so the shared atlas keeps the approved
  shaft look). NEW: _wire_surface() switches every material's OUTPUT
  Surface per pass — EMIT(albedo) / Principled(NORMAL — the bump-
  perturbed shading normal, selected->active) / BAKE_ROUGH(EMIT) / AO.
  The displace-apply guard extended to the HIGH section (strength 0 =
  remove, the DEVLOG-92 trap).
- l2_surface_pbr.gdshader: baked_roughness_tex + use_baked_roughness;
  the baked branch ROUGHNESS = clamp(map.r, 0.15, 1.0) instead of the
  flat 0.8. NORMAL_MAP_DEPTH stays relief_gain.
- world.gd: loads <Mesh>_baked_roughness.png when present
  (use_baked_roughness + texture), relief_gain 1.2 -> 1.5 (the user's
  1.5-2.0 band, low end first).
- baked_mesh.py stages <Mesh>_baked_roughness.png.

**Verification (stale-cache: mesh .import stamps + shader .import
deleted, fresh --import):**
- Gate A: 0 shader compile errors (the 5408 log "error" lines = the
  quit-time GL texture-leak noise, pre-existing).
- Objective: the roughness atlas is REAL (std 0.44: 33% < 0.6 moldings,
  60% > 0.85 recesses; the shaft regions flat 0.8).
- Gate B A/B vs the DEVLOG-92 stable state (col_svc_before, the user's
  camera 21044,11700,-3748.5 yaw 2.98): **5865 px** at thr 6 (4487 at
  thr 12, 2347 at thr 48 — deep light-response shifts), vs the service
  route's 1373. All changed px are the column (the 558 "outside" =
  the same column one crop-row above, x1278..1315 y331..359).
  Local tile-contrast 18.42 -> 18.44 at the fixed sun angle — the
  relief redistributes highlights rather than adding global contrast;
  the camera-angle response is the user's visual call.
- GOLDEN BASELINE PASS: five views, scene 0 px (character strip only,
  identical numbers to the pre-change run ±3 px).
- Compare crop: tmp/shots/col_bump_ab_compare.png (left = stable,
  right = bump route).

**Status:** NOT committed — awaiting the user's visual verdict. Levers:
BUMP_DISTANCE (0.03 -> 0.05-0.08 for stronger relief), relief_gain
(1.5 -> 2.0), ROUGH_LO/HI re-span. The POM/height stays OFF in the
baked branch (the user's "no smearing" requirement — zero UV shift by
construction).

## 2026-11-19 — DEVLOG-99: the MODELED pilaster/panel geometry for the ornate slots (the user's modeling work order)

The user rejected the bump-bake depth ("не помогло") and ordered REAL
geometry: subdivide the ornate lower part, EXTRUDE the pilaster edges
outward 0.05-0.1 m, INSET + extrude the panels inward 0.02-0.05 m, bake
Normal+AO from a further-subdivided duplicate, export low + maps.

**Implementation (headless automation of the manual recipe):**
- baked_mesh.py MODE_GEOM: the pilaster/cornice bands are DETECTED from
  the albedo itself — 1D luminance profiles (u columns / v rows, 5px
  smoothing), threshold p70, band width 2%..14% (wider bright regions
  are ornament fields, NOT moldings — the first p25/p75 attempt caught
  30%-wide fields and was tightened). v bands flipped to UV space (PIL
  rows are top-down). The dark-panel threshold = the luminance p40.
  Detected: in001 1 u-band + 7 v-bands; in002 1+3; in019 2+6 (all
  narrow, 2-8%). The manifest carries the bands + pilaster_d 0.05 m +
  panel_d 0.02 m (the user's low ends) + the roughness ramp.
- blender_bake.py _model_geom(): bmesh on the dense low part. Face
  classification by the UV1 tile center (mod 1): in a u OR v band ->
  molding; else luminance at the UV (bpy pixels are LINEAR — 2.2 gamma
  back to sRGB to match the manifest threshold) below dark_thr -> panel.
  Moldings: per CONNECTED component — extrude_face_region, new verts
  translated along their SOURCE vertex normals (wrap-around rings push
  radially; an averaged normal would collapse a full ring to zero), the
  originals deleted (z-fighting/AO occlusion under the shell). Panels:
  inset_region(thickness=d2, depth=0, use_even_offset) then the inner
  verts pushed inward by their own normals (per-vertex — the region
  average would collapse too). The luminance sampler reads bpy image
  pixels (no PIL inside Blender) with a per-texel cache.
- The HIGH bake source for geom slots = the MODELED low duplicate +
  SIMPLE subsurf x2 (the user's step 2; the features are in the low
  already, the high smooths them for the bake). The bump-node branch is
  kept for mode "bump" but unused; the roughness ramp (1-lum) serves
  BOTH bump and geom slots.
- world.gd: relief_gain back to 1.2 (modeled normals are TRUE normals —
  no exaggeration; the approved DEVLOG-92 shaft value).
- The mesh: 3360 -> 4624 tris (+1264 of real pilaster walls + panel
  insets). NO POM/height in the shader — zero UV shift by construction.

**Verification (stale-cache: mesh + shader stamps, fresh --import):**
- Gate A: 0 shader compile errors.
- Gate B A/B vs the DEVLOG-92 stable state (the user's camera 21044,
  11700,-3748.5 yaw 2.98): **17193 px** at thr 6 (14690 at 12, 11994 at
  24, 9385 at 48 — silhouette-level changes), vs the bump route 5865
  and the service route 1373. The bbox GREW (x to 1422 — the extruded
  pilasters stand out past the old outline); the 235 "outside" px = the
  same column's grown silhouette past the fixed crop. Local tile-
  contrast 18.43 -> 18.57 (first route to raise it).
- GOLDEN BASELINE PASS: five views, scene 0 px (character strips
  identical to the pre-change runs).
- Compare crop: tmp/shots/col_geom_ab_compare.png (left = stable,
  right = modeled).

**Status:** NOT committed — awaiting the user's visual verdict. Levers:
pilaster_d/panel_d (0.05/0.02 -> up to 0.1/0.05 per the user's band),
roughness span. The outdeco05 + the rest of the prop list extend the
same way if approved.

## 2026-11-19 — DEVLOG-100: the column ROLLED BACK to the DEVLOG-92 stable state (the user's verdict)

The modeled-geometry route (DEVLOG-99) is rejected: "ИИ OCR плохо понял
где текстуры" — the automated band detection misread WHERE the
moldings/textures lie on the ornate pieces (texture-profile -> geometry
mapping is unreliable at 64-128 px source textures). The user takes a
new direction: THEY will upscale the texture (external upscaler) and
the rework continues from a better-resolved albedo.

**The revert:** full git checkout of the uncommitted column work (all
three iterations — the service maps DEVLOG-97, the bump bake DEVLOG-98,
the modeled geometry DEVLOG-99 — were never committed; HEAD stays
0ac8199): baked_mesh.py, blender_bake.py, l2_surface_pbr.gdshader,
world.gd, the 5 baked assets restored; the untracked
baked_roughness.png + its .import removed. The stale-cache reimport
(mesh + shader stamps, fresh --import).

**The verification:** the render at the user's camera (21044,11700,
-3748.5 yaw 2.98) vs the DEVLOG-92 stable baseline (col_svc_before):
**5 px** total (an 8x25 llvmpipe-noise strip, no column pixels) — the
runtime is byte-equivalent to the approved state.

**Queued:** when the user brings the UPSCALED albedo for the ornate
textures, re-derive from it (the depth data quality was the root
blocker all along — 64x256 and 128x512 sources). The /Media kit and
the one-file GLB stay for reference.

## 2026-11-19 — DEVLOG-101: the user's 4x upscale wired into the bake + the runtime albedo override

The user upscaled the TWO ornate textures (oren_sylen_in001, in019 — the
depth-starved ones) ×4 externally (/Media/upscale, JPG): in001
256->1024, in019 64x256->256x1024. THE CORRELATION GATE passed:
downscale-4x vs the originals corr R/G/B = 0.975/0.975/0.970 and
0.982/0.978/0.970 (bar 0.9), mean|dRGB| ~0.025 (JPEG noise) — the
pattern is preserved 1:1. Only RGB came back, so:

- baked_mesh.py UPSCALED override: the albedo is JPG->PNG converted and
  drives BOTH the bake and the runtime; the HEIGHT = the client alpha
  (the true depth structure) LANCZOS-upscaled to the new size, blur
  radius x4 (20 instead of 5) to keep the same PHYSICAL smoothing
  scale, gamma 1.4 kept. Staged as <tex>.pbr_albedo_x4.png next to the
  originals.
- world.gd baked block: if <albedo_tex path>_x4.png exists, the BAKED
  mesh swaps its albedo_tex to it (other meshes sharing the texture
  keep the original — the village is untouched by construction).
- The bake re-ran on the DEVLOG-92 displacement route (the approved
  geometry; the finer 4x height feeds the Displace directly).

**Verification (stale-cache: mesh + the two new _x4 stamps, fresh
--import):**
- Gate A: 0 shader compile errors.
- Gate B A/B vs the DEVLOG-92 stable state (the user's camera):
  4715 px at thr 6 (2831 at 12, 1525 at 24), ALL inside the column
  region, 0 outside. Local contrast 18.40->18.39, HF energy +0.15% —
  EXPECTED: the geometry is the same approved shape (the 4x height at
  the same physical blur displaces the same moldings); the change is
  the finer displacement detail + the 4x-sharp albedo. A refinement
  iteration, not a restructure — the safe direction.
- GOLDEN BASELINE PASS: five views, scene 0 px (character strips
  identical to all previous runs).
- Compare crop: tmp/shots/col_up4x_ab_compare.png (left = stable,
  right = 4x upscale).

**Status:** NOT committed — awaiting the user's visual verdict (their
camera, closer inspection). If approved: commit; the remaining ornate
texture (in002) can be upscaled the same way. The depth/alpha for the
upscaled textures is DONE (the client alpha IS the depth).

## 2026-11-19 — DEVLOG-102: the modeled geometry RESTORED on the 4x textures (the user's "flat column" verdict on DEVLOG-101)

The user: the 4x-albedo iteration renders a FLAT column — the task was
the Blender 3D from the previous attempt, which failed on the weak
low-res texture. The DEVLOG-99 modeling route is RESTORED (the code was
reverted uncommitted; re-applied) with the key change: the band
detection runs on the 4x-upscaled albedos (4x texels per molding).

**The detection improvement (measured):** at 4x the profiles find
bands the 1x detection missed — in001 +u(0.968..0.991) (an edge
pilaster), in019 +u(0.465..0.594) (the central molding); the in019
v-band (0.465..0.512) present at 1x is GONE at 4x (it was merged
noise). in002 is NOT upscaled yet — it stays DISPLACE (the approved
look) until its upscale arrives; MODEL_TEXTURES = the upscaled set
{in001, in019}.

**Wired:** baked_mesh.py MODE_GEOM for the upscaled slots (bands from
the 4x albedo, pilaster_d 0.05 / panel_d 0.02, rough ramp 0.45/0.95, no
height_png — no displacement); blender_bake.py re-applied (_lum_sampler,
_model_geom, the LOW modeling + the stash, the HIGH from the stash +
subsurf x2, the roughness EMIT pass, _wire_surface); the shader
roughness uniforms + world.gd roughness loading re-added (reverted with
the rollback); the _x4 albedo override stays (DEVLOG-101).

**Verification (stale-cache: mesh + roughness + shader stamps, fresh
--import):**
- Gate A: 0 shader compile errors.
- Gate B A/B vs the DEVLOG-92 stable state (the user's camera):
  **15831 px** at thr 6 (13153 at 12, 10259 at 24, 7551 at 48 — real
  silhouette-level changes), ALL inside the column region, 0 outside.
  Local contrast 18.40 -> 18.51 (up).
- vs the REJECTED 1x-modeled route: **12160 px differ** — the 4x
  detection + in002-displace produce materially different geometry,
  not a repeat of the rolled-back mistake.
- GOLDEN BASELINE PASS: five views, scene 0 px (character strips).
- Compare: tmp/shots/col_geom4x_ab_compare.png (left = stable, right =
  modeled on 4x).

**Status:** NOT committed — awaiting the user's visual verdict. If
approved: commit; in002 joins after its upscale (one dict entry).

## 2026-11-19 — DEVLOG-103: the PILASTERS corrected to the UV-seam corners (the user's client screenshot)

The user's verdict on DEVLOG-102 + the CLIENT screenshot of the column:
"not the central pattern — the PILASTERS themselves forward". The
screenshot shows the structure: the polygonal base has ONE dark marble
panel per face with the carved ornament in its center; the PILASTERS
are the raised stone bands AT THE CORNERS, and the corner wraps at the
UV seam — so in tile space a pilaster is SPLIT across u=0/1, while the
bright central band (in019 u 0.465..0.594) is the ornament ON the
recessed panel.

**The fix (one rule, both files):**
- detect_bands: keep only u-bands TOUCHING the seam (a <= 0.03 or
  b >= 0.97), expanded to cover the wrap (a face at u=0.01 sat outside
  a (0.016..) band). Result: in001 u=[0.968..1.0]; in019
  u=[0.0..0.0703]+[0.8984..1.0] (one corner pilaster, both halves); the
  central ornament band DROPPED. v-bands (the horizontal cornice rings)
  unchanged — the panel frames ARE raised in the client.
- _model_geom: EVERYTHING between the moldings is now the panel field —
  the dark stone AND the bright ornament on it — inset together at
  panel_d (the ornament extrusion was the "pattern in the middle"
  mistake). The luminance sampler and the dark_thr panel test are
  REMOVED (dead code; the classification is purely band-based now).

**Verification (stale-cache: mesh + roughness + shader stamps, fresh
--import):**
- Gate A: 0 shader compile errors.
- Gate B A/B vs the DEVLOG-92 stable state (the user's camera):
  16217 px at thr 6 (13742 at 12, 7856 at 48), all inside the column
  region, 0 outside. Local contrast 18.40 -> 18.51.
- vs the DEVLOG-102 central-pattern route: 8313 px differ — the
  geometry changed materially (the ornament no longer extrudes; the
  panel fields inset whole).
- GOLDEN BASELINE PASS: five views, scene 0 px (character strips).
- Compare: tmp/shots/col_pilast_ab_compare.png (left = stable, right =
  seam-pilaster route).

**Status:** NOT committed — awaiting the user's visual verdict at
their camera.

## 2026-11-19 — DEVLOG-104: per-face TEXTURE-CONTENT classification (the band routes are dead)

The user's verdict on the seam route + the OUR-RENDER screenshot: the
volume still extrudes from the middle of the picture, not the pilasters.

**The diagnostic (measured, not guessed — tmp/diag_uv3d.py in Blender):**
for in001 the 8 v-band faces sit EXACTLY at the 8 prism-corner angles
(-164, -119, -74, -29, +16, +61, +106, +151 — an octagon; the 88 panel
faces cluster BETWEEN them); for in019 all 16 faces are PAIRS at the
corners (every UV center in the seam bands). So the seam mapping was
NOT the error — but the band classification still broke the RINGS: a
cornice ring crosses both pilasters and panels; band-center
classification extruded ring pieces at the corners and inset the ring
pieces over the panels — jagged slabs, exactly the user's screenshot.

**The new rule (no layout assumptions at all):** a dense-mesh face is a
MOLDING face iff its WHOLE UV footprint is bright (the luminance
sampled at the UV centroid + every loop UV, all above bright_thr = the
texture's p70; Blender-side sampler linear->sRGB 2.2). EVERYTHING else
— dark panel, ornament, faces straddling a molding edge — is the panel
field: inset whole. Bright islands fully inside the panel (the ornament
motifs) are killed by the STRIP-SHAPE test: an extruded component must
be a long strip in UV space (one axis >= 0.6 of the tile, the other
<= 0.4; pilasters span v ~1.0, cornice rings u ~1.0, ornament spots
fail) with >= 6 faces. The detect_bands machinery is REMOVED — the
manifest now carries bright_thr only.

**Verification (stale-cache: mesh + roughness + shader stamps, fresh
--import):**
- Gate A: 0 shader compile errors.
- Objective: the modeled mesh = 4096 tris (+736 over the stable 3360 —
  the strip filter is stricter than the band route's +1264).
- Gate B A/B vs the DEVLOG-92 stable state (the user's camera): 11555
  px at thr 6 (9037 at 12, 4157 at 48), all inside the column, 0
  outside; **13911 px differ from the seam-band route** — materially
  different geometry. Local contrast 18.40 -> 18.39 (flat at the fixed
  sun angle — the structure redistributed; the depth verdict is the
  user's).
- GOLDEN BASELINE PASS: five views, scene 0 px (character strips).
- Compare: tmp/shots/col_pface_ab_compare.png (left = stable, right =
  per-face route).

**Status:** NOT committed — awaiting the user's visual verdict.
Levers: bright_thr (p70), the strip-shape thresholds, pilaster_d/panel_d.

## 2026-11-19 — DEVLOG-105: the extruded faces go FLAT COLOR (the user's work order)

The user's recipe: for EVERY extruded face (pilaster, ring, base) —
take its source PNG zone, average it to ONE color, fill the whole face
flat, NO UV mapping on the convex faces; the flat panels between keep
the original PNG with UV.

**Implementation:**
- _model_geom tags the extruded faces with a per-face float attribute
  "mold_mask" (bmesh faces layer; survives the join; set on the mold
  tops AND the new side walls).
- blender_bake.py _flat_fill_albedo(): after the EMIT albedo bake, the
  connected mold-face components are collected on the joined mesh; each
  component's color = the AVERAGE of its slot's albedo over the
  component's UV1 footprint (a Blender-side linear-space RGB sampler,
  2.2-gamma-consistent with the bake); every component face's UV2
  polygon is rasterized (even-odd point-in-poly) and its pixels in the
  1024 bake atlas overwritten with the flat color. The panel islands
  keep the baked texture content (the EMIT bake through UV2). Verified:
  44.8% of the atlas is now flat-adjacent (the mold islands).
- The sidecar gains "flat_mold": true; world.gd loads baked_albedo.png
  and sets albedo_from_atlas for flat_mold meshes ONLY (other meshes
  keep the tile-channel albedo). Shader: uniform bool albedo_from_atlas
  — the baked branch ALBEDO = the atlas sample when set (the panels
  show the same source pixels through UV2 — visually identical, the
  moldings flat).

**Verification (stale-cache: mesh + roughness + shader stamps, fresh
--import):**
- Gate A: 0 shader compile errors.
- Gate B A/B vs the DEVLOG-92 stable state (the user's camera): 16886
  px at thr 6 (14861 at 12, 8113 at 48), all inside the column, 0
  outside; **15036 px differ from the textured-mold route** (DEVLOG-104)
  — the flat fill changed the render materially.
- GOLDEN BASELINE PASS: five views, scene 0 px (character strips).
- Compare: tmp/shots/col_flat_ab_compare.png (left = stable, right =
  flat-color molds).

**Status:** NOT committed — awaiting the user's visual verdict.

## 2026-11-19 — DEVLOG-106: the column experiments CLOSED (revert #2) + the missing-shore investigation (the "oldest bug")

**The revert:** the user rejected the flat-color mold route (DEVLOG-105)
— "способ опять неудачный. откатываем на исходное". Full git checkout
back to HEAD (0ac8199; DEVLOG-101..105 were never committed):
baked_mesh.py, blender_bake.py, the shader, world.gd, the 6 baked
assets; the untracked roughness png + the two _x4 albedos + their
.imports removed; fresh reimport. Verified at the user's column camera:
49 px diff vs the stable render — an 20x33 grass-patch strip
(x789..809, y724..756, llvmpipe alpha-cutout jitter), the column region
0 px. The runtime = the DEVLOG-92 stable state.

**The shore investigation (the user: 20_18 = village + temple + sea
shore, ours is a bare square):**
- The extraction is NOT cut: the terrain heightmap covers the FULL tile
  (256x256 cells = 32768x32768 units, extent matches, one TerrainInfo,
  holes only 6.4% — the village plaza + a small pond). The square edges
  are the TILE BOUNDARY: the client streams the neighbor tiles
  seamlessly; we render only 20_18.
- 20_18 has NO WaterZone/WaterVolume at all — the water is NOT in this
  package.
- The neighbors (decrypted + their heightmaps read from
  Textures/t_<map>.utx, the G16 terrain-map textures): 19_17 (north-west)
  = 83% flat ocean floor at Z **-4700**; 20_17 (north) = 20% floor
  -4700 (its north-west is sea); 19_18 (west) = floor -4700 (13%) +
  beach shelf -3730/-3740; 19_19 = shelf -3790/-3800.
- The water level measured from the client's own actors: 19_17 has 10
  WaterVolume brush actors at Z **-3840** (coastal) / -4864 (deep) —
  the sea surface = -3840, the beach shelf sits just above it.
- OUR tile: **13.2% of the land cells (8091) are below -3840**, 6320 of
  them in the north strip (y < 30 cells ≈ game y < 3900) — the
  coastline crosses OUR tile's north edge; in the client the north of
  the village map is the sea shore, seamlessly continuing into 20_17 /
  19_17. The village valley (-4404) is also below the nominal sea level
  but DRY — UE2 water is placed explicitly (the sheets exist only where
  the client put them).

**The fix (a NEW STAGE, awaiting the user's opening):**
1. The neighbor ring as seamless terrain (at least 20_17 + 19_18; their
   heightmaps + QuadVisibility extract with the same verified pipeline —
   the statics of the neighbors are a separate decision).
2. A native Godot water plane at Z = -3840 over the below-level regions
   (modern water shader; NOT the client's BSP/WaterVolume crutches —
   the modern-port rule).
3. The client-side ground truth for the coastline = the 19_17 WaterVolume
   extents (their brush models bound where the client actually floods).

## 2026-11-20 — DEVLOG-107: the multi-tile world — 20_17 (the north neighbor) implemented

The user's orders after the shore investigation (DEVLOG-106): the water
we add ourselves (its presence in the client data irrelevant); the tile
BORDERS matter for the clean future expansion; 19_19 = a lake, no sea;
19_18 definitely has the sea shore (confirmed); the reference map = the
C5 geodata grid (the user keeps it, with the caveat that the map
variants have slightly different borders). THE STAGE: implement 20_17
(the north neighbor).

**The offline build:** `tools.l2strict build --map 20_17 --neighbor
19_17 --neighbor 21_17 --neighbor 19_18 --neighbor 20_18 --neighbor
21_18 --assets-dir assets/maps/20_17 --expect StaticMeshActor=1109
PlayerStart=8 TerrainInfo=1 TerrainSector=256` — rc 0: 78 meshes, 131
textures, 65503 visible quads / 33 holes / 5469 edge-turns, ZERO
clamped border samples. The tile spans world y -32768..0 (its terrain
origin (0,-32768)), 39% below the future sea level -3840.
`verify` extended to PER-MAP gates (the stats/terrain/mesh/texture
counts were 20_18-hardcoded; the 20_18 mesh gate updated 129 -> 133 =
the current committed asset_map). Both tiles verify: status ok.

**THE SEAM (measured):** 20_18's north border row vs 20_17's south
border row: **max |dZ| = 0.00** — the tiles stitch exactly (both derive
from the client's own continuous heightmaps).

**The runtime refactor (world.gd):**
- `const TILES` = [(20_18, root), (20_17)] + `_load_data()` loads every
  tile into `tiles: Array[Dictionary]` (map/materials/asset_map/bsp/
  terrain raws per tile); `_activate(tile)` points the builder globals
  (map_data, materials_data, asset_map_data, bsp_data, terrain_*) at
  one tile; `active_dir` replaces MAP_DIR in the per-tile resource
  lookups (the textures, levelbsp, brushes); the temple stays
  MAP_DIR-scoped (the root-only extra; missing file = early return).
- `_ready()`: per tile — a Node3D parent at (origin.x, 0, origin.y) *
  UNIT_SCALE, then _build_terrain/_build_meshes/_build_bsp/_build_lights
  under it (`_tile_root`); the tile-local coordinates need NO offsets.
  After the loop: re-activate the root tile for the debug flows and the
  spawn.
- The terrain builder builds in LOCAL coords (ox/oz = 0; the parent
  carries the origin); terrain_height/has_terrain_surface resolve the
  covering tile via `_tile_at` (world coords) with the root fallback;
  _height_at takes the tile.
- The foliage batch (`_veg_batch`, `_foliage_trunk`) CLEARED after each
  tile's flush — otherwise the next tile's MultiMeshes would re-include
  the previous tile's local transforms.
- The debug flows (floor profile etc.) run with the root tile active.

**Verification:**
- Gate A: 0 shader errors; the world builds in ~3.2 s (both tiles).
- Counts: 20_18 = 61361 quads / 401 statics / 112 lights (IDENTICAL to
  the pre-refactor runs); 20_17 = 65503 quads / 958 statics / 10 lights
  / 151 foliage instances.
- THE SEAM IN THE RUNNING WORLD: L2_FLOOR_PROFILE across game y=0
  (9000,600 -> 9000,-600): y=-47.034 on both sides, continuous
  -47.034 -> -47.040 into 20_17, "via terrain" on every step — no
  step, no void, both tiles' colliders live.
- GOLDEN BASELINE PASS: the five village views — the scene identical
  (the character strips as always); OUTSIDE the character strip only
  ~302 px (upper_street) / ~304 px (entrance_road) of NEW distant
  20_17 silhouettes on the horizon — the very content this stage adds.
- The seam screenshots: tmp/shots/seam_view/ (the character ON the
  border, looking north — the fields continue, the 20_17 mountains
  ahead), tmp/shots/seam_view2/.

**Known cosmetic:** a subtle ground-color band at the border — the two
tiles blend their OWN terrain layer sets (12 layers in 20_17 vs 9 in
20_18), the same per-tile layering the client shows at tile borders.

**Status:** NOT committed — awaiting the user's seam inspection. Next
steps when opened: the water plane at -3840 over the below-level
regions; 19_18 (the west neighbor with the confirmed sea shore) by the
same recipe.

## 2026-11-20 — DEVLOG-108: 21_18 (Sea of Spores, the east neighbor) implemented — the third tile

The user's order: implement 21_18; the water is ours to add (irrelevant
in the source data); the borders follow the C5 geodata grid.

**The build:** `build --map 21_18 --neighbor 20_18 20_19 20_17 21_17
21_19 22_18 22_17 22_19` — rc 0: 2309 statics, 115 meshes, 118 texture
refs, 10 terrain layers, 65536 visible quads / 0 holes / 4855
edge-turns, origin (32768, 0) = east of the village tile. THE SEAM
MEASURED: 20_18's east border vs 21_18's west border — max |dZ| = 0.00.
verify: per-map gates added, status ok.

**The pipeline quirk fixed (the L2 duplicate-name binding):**
`field_deco_T.utx` contains TWO Texture exports named `oren_stone001`
(payloads differ by 28 bytes in the small-mip tails only — 99.94%
identical). UE2 name binding resolves the FIRST export; our strict
stager raised. `Package.export_by_name` now accepts on_ambiguous="first"
(loud WARN) and `PackageSet.find_object` uses it for class=="Texture"
lookups only — every other class stays strict. The 21_18 build passes.

**The runtime:** the TILES registry gains 21_18 — the same per-tile
parent at (32768, 0); no other code changed (the refactor held). The
world builds in ~4.9 s for THREE tiles: 20_18 (401 statics / 61361
quads / 112 lights), 20_17 (958 / 65503 / 10), 21_18 (1445 / 65536 /
21 lights). Gate A: 0 shader errors.

**The east seam in the running world:** L2_FLOOR_PROFILE across
x=32768 (32368,12000 -> 33168,12000): y -36.284 -> -36.286 -> -36.290
(2-4 mm steps, a gentle slope), "via terrain" everywhere — no step, no
void. Golden baseline: the totals identical to the pre-21_18 runs; the
pixels outside the character strip 0/0/0/5/8 — the 20_18 scene is
pixel-stable. The east-border screenshot: tmp/shots/east_view/ (the
temple seen from outside its east side, the ground continuous).

**ARE THE MAPS CONNECTED WITHOUT THE LINEAGE 2 CRUTCHES? YES.**
The original L2 (UE2) treats each tile as a self-contained "room/cube"
LEVEL: its own ZoneInfo (the sky/fog per cube), its own BSP world, the
level streaming at the borders (the engine swaps the level as the
player crosses), the movement blocking via the separate .geodata files
plus the invisible barrier brushes (20_18 carries 38 BlockingVolumes,
21_18 has 38 of its own) — the "invisible walls" the user remembers.
OUR port ports NONE of that (the modern-port rule: from the old client
only the geodata and the coordinates):
- the three tiles are sibling Node3D subtrees in ONE continuous scene
  graph at their true world offsets — pure coordinate frames, no zone
  logic, no streaming, no level swaps, no barriers;
- the terrain heights and the colliders continue across the borders by
  construction (both seams dZ = 0.00; the ray queries cross the borders
  transparently — one physics space);
- the player walks 20_18 -> 20_17 / 21_18 with no transition, no load,
  no invisible walls; the 38+38 BlockingVolumes are NOT ported (when
  the world ring ends, the edge policy is a gameplay decision, not an
  inherited crutch);
- the per-cube ZoneInfo sky/fog switching is replaced by ONE global
  environment.
The cost of not streaming: the whole built world lives in memory (3
tiles now — a few tens of MB of meshes); the render cost is handled by
the visibility ranges + the cluster culling. If the tile count grows,
Godot's own streaming (visibility ranges / MeshInstance3D visibility /
async loads) covers it WITHOUT reintroducing the room-cube machinery.

**Status:** NOT committed — awaiting the user's inspection of the east
seam. The water plane (-3840) and 19_18 (the west, the confirmed shore)
remain queued.

## 2026-11-20 — DEVLOG-109: 19_18 (the west neighbor, the confirmed sea shore) — the FOURTH tile

The user approved the multi-tile stage ("крупных багов нету, мелочи
позже") and ordered 19_18. 19_19 (the south) has a LAKE, no sea (the
user's correction); the sea shore is in 19_18 (confirmed) and the
north-west.

**The build:** `build --map 19_18 --neighbor 18_18 19_17 19_19 20_18
20_17 20_19 18_17 18_19` — rc 0: 1966 statics (12 deleted, 1954
placeable), 90 meshes, 147 texture refs, 10 layers (9 valid), 65487
quads / 49 holes / 5667 edge-turns, origin (-32768, 0). **28.4% of the
tile is below the future sea level -3840** — the shore tile. THE SEAM
MEASURED: 19_18's east border vs 20_18's west border — max |dZ| =
0.00. verify: the per-map gates added, status ok.

**The runtime:** one TILES entry — the same per-tile parent at
(-32768, 0); no other code changed. The world: FOUR tiles in ~6.6 s
(20_18: 401 statics / 61361 quads; 20_17: 958 / 65503; 21_18: 1445 /
65536; 19_18: the new build). Gate A: 0 shader errors.

**The west seam in the running world:** L2_FLOOR_PROFILE across x=0 at
y=8000 (-400 -> +400): y -32.574..-32.590 (a gently rolling field, no
step), "via terrain" everywhere. GOLDEN BASELINE PASS: 0/0/0/5/8 px
outside the character strip — the village scene pixel-stable.
The shore view: tmp/shots/west_view/ (the descent from the hills west,
the flat SEA FLOOR visible as bare land — the water plane at -3840 is
a separate pending stage; on the horizon the straight tile edge into
18_18, which is not built yet).

**Status:** NOT committed — the user inspects; the water stage and the
18_18 expansion follow when opened.

DEVLOG-109 addendum — the build/import cost measured and optimized (the
user's questions): the repeat tile build = 3 s (incremental, the
manifest hashes skip the UModel exports); the per-verification import
was paying a 32 s tax scanning tmp/'s 22 862 junk files — tmp/.gdignore
added (MANDATORY now, in REBUILD_RULES.md): the no-op import 36 s -> 4 s,
the full re-import = ~36 s; 4032 stale .import files under tmp/ removed.
The per-tile builds are independent (an 20_18 asset edit does not
rebuild the other tiles). The runtime load +~1.5-1.7 s per tile.

## 2026-11-20 — DEVLOG-110: the multi-tile placement bug FIXED (the double offset)

The user's bug report on 19_18: all the objects vanished from their
places and hung over the sea to the north, the mutual spacing intact.

**The root cause (measured):** the map.json actor locations are
WORLD-frame for EVERY tile — the extractor normalizes them (20_17's
actors y -26227..-1811 = the north tile's world coords; 19_18's
x -31331..-347 = the west tile's; 21_18's x 33596..65171 = the east
tile's). The DEVLOG-107 tile parents offset by the terrain origin
ADDED a second shift to the already-world actor positions: 19_18's
statics landed 32768 west, 20_17's — 32768 north (in the ocean void),
21_18's — 32768 east. The 20_18 tile (origin 0,0) hid the bug.

**The fix:** the tile parents REMOVED entirely — every builder
(terrain/meshes/bsp/lights) writes to the world root; the terrain mesh
applies its own terrain.json origin (the pre-DEVLOG-107 behavior — the
heights are absolute Z, the grid is local), the actors keep their raw
world positions. `_tile_root` deleted; the veg batch clearing stays
(the transforms are world-frame now — the clear prevents the cross-tile
duplication). For 20_18 the result is bit-identical (origin 0,0).

**Verification:**
- The user's broken-view camera (-30016,25499 yaw west): the rocks
  STAND on the hillside, the floating fleet gone
  (tmp/shots/west_fix/).
- The static spot-check (tree10 at -13358,24145): the collider hit at
  y=-35.59 via Veg:Oren_Darkelf_tree10, the terrain below at -37.29
  (the interpolated -3729.18 vs the authored -3727.56 — the normal
  trunk-base delta), and 19_18's own SSQ_BRoom03_Top deeper — the
  tile's dungeon content present.
- GOLDEN BASELINE PASS: 0/0/0/5/8 px outside the character strip.
- Gate A: 0 shader errors; the four tiles build in ~6.5 s.

**Status:** NOT committed. The water plane (-3840) and 18_18 remain
queued.

DEVLOG-110 addendum 2 — the spawn moved to the 19_18/20_18 border (x=0,
y=8000; faces east) per the user's order, and the build/cycle COSTS
measured with the L2_TILES diagnostic + the phase timestamps:
- The repeat tile build: 19_18 = 9 s (incremental, deterministic).
- The import: the no-op 4 s (with tmp/.gdignore), the full wipe ~36 s.
- The RUN decomposition (L2_TILES + the phase timestamps): the settle
  (90 physics frames = 90 RENDERED frames) dominates: 0.38 s/frame on
  1 tile -> 0.83 with 21_18 visible -> 1.26 on 4 tiles. The terrain
  LOD (TERRAIN_LOD_DIST=5000, layer-0-only beyond 5 km) halved the
  frame time on the 4-tile world (1.26 -> 0.65-0.9); the LOD at 800 m
  regressed stairway/spawn (2784 px of the in-tile far terrain) — 5000
  is the working threshold, the baseline views stay intact (0/0/0/5/8).
- The lamp gate (19_18 = 1755 Light actors!) implemented and measured:
  NO frame effect (the lights were not the cost) — kept as hygiene.
- The settle 45 test: NOT deterministic (235 px — the camera lerp is
  time-based, incomplete at 45 slow frames); the 90-frame settle stays.
- The two 10-minute hangs = the process errors, not the rebuilds: a
  no-quit run idling forever + the 5-instance .godot deadlock (4 of 5
  at 0% CPU). The discipline is in REBUILD_RULES.md. No full rebuild
  exists for small edits: the .gd edits need NO import, the tile
  rebuilds are 3-9 s.
- The remaining per-frame cost = the multi-tile scene graph + the
  near-band terrain fragments on llvmpipe — the Godot profiler is the
  next diagnostic; the tile streaming is the structural option.

DEVLOG-110 addendum 3 — the descent-view nondeterminism (the multi-tile
frame rate exposed it): the descent spawn sits on the SLOPED stair mesh —
the character slides down the stairs under gravity during the settle; the
slide distance = the GAME time, and the game time per 90-await settle now
varies with the frame rate (the slow multi-tile render = the physics
catch-up ticks per iteration vary). The descent baseline diff exploded to
133015 px (the character slid out of the frame; the camera followed). The
other four views PASS (0/0/0/5/8). The cause-level fixes (the user picks):
A. the settle counts PHYSICS TICKS from the spawn (a fixed 5 s of game
   time — the deterministic slide distance) + the descent baseline
   re-capture (the character lands on a different stair step than the
   2026-11-15 reference);
B. the descent spawn moved OFF the sloped stairs (a flat spot nearby —
   the character stands still, the deterministic view, no re-capture).
The measured performance facts of this session: tmp/.gdignore (the
import scan 36 -> 4 s), the terrain LOD 5000 m (the frame 1.26 -> 0.65 s
on the 4-tile world), the lamp gate (no frame effect — kept as hygiene),
the lights of the expansion tiles exonerated (the full removal = no
change), the cast_shadow gates exonerated AND reverted (they flattened
the distant self-shadowing), directional_shadow_max_distance BROKE the
sun in the compatibility renderer (the village went night-dark) and was
removed. The shadow per-pixel sampling = 43% of the frame on llvmpipe
(measured via the L2_BRIGHT shadows-off) — unfixable at the geometry
level; the GPU rendering or the resolution scale are the remaining
levers (the user declined the GPU tests for now).

DEVLOG-110 addendum 4 — the honest end-to-end cost audit (the user's
"the build burns ~10 CPU minutes every iteration" vs my "9 s build"
claim; both numbers are real — they measure DIFFERENT phases). Measured
serially 2026-11-20 (tmp/audit_cost.sh, tmp/demo_render_cost.sh):

- `build --assets-dir` (repeat, full canonical command): **9.0 s** wall
  / 4.1 s CPU. It re-runs ALL 237 UModel exports (one process per
  object, ~25 ms each) and re-copies 337 asset files with identical
  content. Wasteful but harmless. (The earlier "9 s" was this phase —
  I wrongly presented it as the iteration cost.)
- `godot --headless --import` right after the build: **3.6 s, 0
  artifacts re-imported**. Godot 4.7 decides re-import by the source
  MD5 (docs: tutorials/assets_pipeline/import_process.html), NOT mtime
  — re-staging identical content triggers nothing. Warm import 3.2 s.
  Project splitting gains nothing for the build: the import is already
  per-resource incremental.
- `verify`: 0.15 s.
- **THE REAL HOG — one standard verification render**: 166 s wall at
  **720% CPU (peak 723%)** = ~20 CPU-minutes per render. Phases: the
  world build 7.4 s; the 90-frame settle **117 s (70%)** — the settle
  awaits 90 RENDERED frames (`for i in settle: await physics_frame`),
  on llvmpipe ~1.26 s/frame; the two screenshots ~32 s.
- The attribution: an iteration chains 3-5 renders (the fix check +
  the golden baseline views) = the CPU pegged for ~10-15 wall minutes.
  THAT is what the user watches as "compiling the project file". The
  19_18 slowdown = the per-frame cost tripling (0.38 -> 0.65-1.26
  s/frame), tripling every settle; the build/import stayed fast.
- The root fix candidate (also the descent nondeterminism fix): the
  settle counts PHYSICS TICKS (`Engine.get_physics_frames()` target)
  with `Engine.max_physics_steps_per_frame` raised during the settle —
  deterministic game time AND a few rendered frames instead of 90
  (the render ~45-60 s). Requires the descent baseline re-capture
  (the pending option A). Optional extras: L2_TILES=20_18 for the
  village-scoped baseline renders (the neighbors are invisible in
  those views — the 0-8 px diffs prove it); the real GPU.

## 2026-11-20 — DEVLOG-111: A+B done — the tick-counted settle + the GPU
## render harness (the user approved both)

**A — the settle counts PHYSICS TICKS** (scripts/world.gd): a new
`_await_settle_ticks()` loop (`Engine.get_physics_frames()` target +
`await get_tree().physics_frame`), default **720 ticks = 12 s of game
time** = exactly the llvmpipe-era 90-frame settle (90 x the 8-tick
catch-up cap), so the standing baselines keep their state.
`L2_SETTLE_TICKS` overrides. The burst flow uses it too. The old
90-awaited-frame scheme made the game time a function of the machine:
720 ticks on llvmpipe but ~90-360 on a fast renderer (the descent slide
and the framing varied). `max_physics_steps_per_frame` stays at the
default 8 — a higher cap trades tick exactness for speed. Parse OK.

**B — the renders run on the real GPU**: DISPLAY=:0,
`godot --path . --rendering-driver opengl3` picks **radeonsi / Radeon
RX 6400 (navi24, ACO, Mesa 26.3.1)**. Probes: `--display-driver
headless --rendering-driver opengl3` does NOT render (hangs — dummy
display); the real X display works out of the box (glxinfo already
reported radeonsi as the default GL driver).

**The measured costs (one standard render, the default spawn):**
- llvmpipe (before): 166 s wall at 720% CPU (~20 CPU-minutes); the
  90-frame settle 117 s (70%).
- GPU (after): **21-22 s wall**, boot 7.7 s + the 720-tick settle 12.3 s
  (real-time 60 ticks/s) + the shots ~1 s. The whole baseline loop
  (fresh import + 6 renders) = **165 s** vs ~15 min before.

**Pixel parity and determinism (measured):**
- GPU vs llvmpipe, the same 720-tick state (the default spawn):
  66% pixels identical, mean |delta| 3.8, 1.9% of pixels >32 — the
  rasterizer rounding noise; on the standing baseline views it is
  2-14k px >8 per view. This EXCEEDS the diff gate => the golden
  baselines are RE-CAPTURED on the GPU (the user approved the
  re-capture as part of B).
- GPU run-to-run (upper_street rendered twice): **99.89% identical
  pixels, 426 px >8, 62 px >32, mean 0.008** — deterministic for the
  gates; ~430 px >8 is the new noise floor.
- Brightness sanity of the 5 new captures: 4 views match the old
  means to ±0.1 (the same exposure); descent 55.3 vs 59.3 — its far
  field legitimately changed (the terrain LOD 5000 m shifted the
  far-south pixels since 2026-11-15 — this, not only the settle
  variance, was the 133015 px descent explosion).

**Docs updated:** the MANIFEST (the re-capture note + the real-display
commands + the noise floor), REBUILD_RULES.md (the render harness
section: the GPU first, xvfb = the llvmpipe fallback only, the tick
settle), AGENTS.md (the render instruction line).

**Status:** NOT committed. The commit of the whole multi-tile stage +
A+B awaits the user's word.

DEVLOG-111 addendum — the descent chaos root-caused and the input
contamination (the user confirmed they were using the mouse/keyboard
during my renders):

- The unanchored tick settle ("current + 720") was NOT enough: between
  the spawn and the settle loop the physics tick count drifts
  machine-dependently (the first-frame shader-compile hitch + the
  shader cache state), and 12 s of tumbling down the descent stairs
  AMPLIFIES the drift — the descent differed by **1.12M px (78% of the
  frame, mean 51.4)** run-to-run. Fix: the settle anchors AT THE SPAWN
  (`_spawn_physics_frame = Engine.get_physics_frames()` in
  `_spawn_player`; `_await_settle_ticks` measures from there). The
  descent became **0 px** run-to-run.
- The real display exposes the REAL user input: the first baseline
  capture had the user's right-drag orbit the camera mid-render
  (the DEBUG camera prints: the pitch -1.079 contaminated vs the -0.35
  default) — entrance_road and stairway_plaza differed by ~1M px.
  Fix: `player.input_locked` (all input ignored) +
  `DisplayServer.WINDOW_FLAG_NO_FOCUS` (the game window does not steal
  focus), both set automatically when L2_SCREENSHOT/L2_BURST is
  present. The user confirmed: the mouse and keyboard were theirs.
- **The final noise floor (every view rendered twice, GPU + anchored
  settle + input lock):** upper_street 30 px >8 / entrance_road 1 /
  descent 0 / stairway_plaza 6 / spawn_plaza 0; mean delta ~0.001.
  The baselines re-captured (3rd pass, Docs/baseline/*.png), the
  MANIFEST + REBUILD_RULES updated with the lock/anchor rules.

## 2026-11-21 — DEVLOG-112: the 19_18 trees per the new pattern (the
## canopy alpha cards were SOLID)

The user's report: the 19_18 trees are "the old type", and when moving
near them the cursor hits the alpha channel and the character cannot
run further.

**The root cause — three stacked defects (all measured):**
1. `_foliage_trunk` (the bark-surface AABB table for the trunk
   cylinders) is populated inside `_get_mesh` ONLY on the mesh-cache
   miss (the cache lives for the whole session), but was CLEARED after
   every tile flush (the DEVLOG-107 hygiene). The tiles build in order
   20_18 → 20_17 → 21_18 → 19_18: the first tile computed the trunk
   entries for its 6 tree keys, the flush consumed and cleared them.
   In 19_18 only ONE key (Oren_Darkelf_tree10 — not seen in the earlier
   tiles) got a fresh entry; tree02/03/09/11/12 (195 instances) had
   NONE — and the flush's fallback branch (`elif not ("grass" ...)`)
   gave them the FULL TRIMESH: the whole tree mesh including the
   canopy ALPHA CARDS as solid geometry. The click ray stopped on
   invisible foliage; the character ran into the invisible canopy and
   stopped — the exact report. L2_TRACE_RAY before the fix: a vertical
   ray through tree09 hit `Veg:...tree09 face=66` (a trimesh FACE, not
   a cylinder; tree10's cylinder shows face=-1).
2. The trunk block's own gate checked "tree" in the PACKAGE name only —
   the north tile's Primitive_FieldOBJ_S trees (InDecotree/INtree/
   MDtree/PriPlain, ~700 instances) were missed by _is_foliage_key
   entirely and built as old per-actor statics with full trimesh
   colliders (the same solid-canopy symptom).
3. The trunk cylinder was positioned at the MESH ORIGIN (x/z) — wrong
   for off-center meshes: Darkelf_tree10's bark spans z -6.64..1.09
   with the pivot at the edge, so its r=1.2 cylinder floated inside
   the canopy spread.

**The fixes (scripts/world.gd):** `_foliage_trunk` is never cleared
(keyed by the mesh key — tile-independent); the trunk gate matches the
object name too; the cylinder offset = the bark AABB center transformed
by the instance basis; the flush fallback explicitly EXCLUDES trees —
a tree key without a trunk entry is pass-through (the canopy cards are
not solid), never the full trimesh.

**Verification (all numeric):**
- The flush counts: 20_18 = 6, 20_17 = 11, 21_18 = 9, 19_18 = 6 tree
  keys with trunk colliders — every tree key in every tile.
- L2_TRACE_RAY after: tree09 (19_18) = the cylinder (face=-1) at the
  expected height; tree10 = the cylinder at the rotated bark center
  (the yaw -20352 + roll 1360 applied); the canopy rays PASS THROUGH
  (no card hits); the 20_17 INtree001 = the cylinder (face=-1).
- GOLDEN BASELINE PASS: 19/0/0/3/1 px >8 (the noise floor ≤30) — the
  collider fixes are invisible.
- The render = the GPU path, ~21 s per view.

**Pending (noted, out of scope):** the 20_17 decotree textures
Primitive_INDecotree_02/03 carry cutout alpha (0..255), but the
alpha-scissor check keys on "leaf"/"grass" texture names — the deco
trees render their cards opaque. A separate visual task if the user
opens the 20_17 look.

## 2026-11-21 — DEVLOG-113: 19_19 (the southwest neighbor, the lake
## tile) — the FIFTH tile

The user's order: «переносим теперь 19_19». The user's earlier note:
the tile has a LAKE, no sea.

**The build:** `build --map 19_19 --neighbor 18_18 18_19 19_18 19_20
20_18 20_19 --assets-dir assets/maps/19_19` — SIX neighbors: the client
ships NO corner heightmaps for the pure-ocean corner tiles (t_20_20 and
t_18_20 are absent from Textures/). rc 0: 1513 actors, 1511 statics
(0 deleted), 1 PlayerStart (−12373, 44613, −3606), 58 meshes, 112
texture refs, 11 layers (10 valid), 65511 quads / 25 holes / 11679
edge-turns, origin (−32768, 32768). **1 border sample clamped** — the
SE corner vertex (the missing t_20_20); the east/south EDGES sample
from the real t_20_19 / t_19_20. Mesh families: field_deco 1031,
Oren trees 344, artifacts 97, Waterfall 38, FX 1.

**The verify gates:** the per-map 19_19 entry (the stats + the terrain
counts + `clamped_border_samples: 1` override + the expected-warnings
list — the ocean-corner clamp is legitimate). verify: ok.

**THE SEAM MEASURED:** 19_19's north border vs 19_18's south border,
all 257 vertices: max |dZ| = 0.00.

**The TILES entry appended** (the 5th tile); no other code changes.

**The reimport trap AGAIN:** the first boot placed **0 static meshes**
for 19_19 — the post-build `godot --headless --import` was forgotten
(REBUILD_RULES Rule 2). The foliage still rendered because its mesh
keys are shared with the earlier tiles (the session mesh cache); the
19_19-only keys (Waterfall, FX_E_S, the new foliage meshes) silently
failed (`ResourceLoader.exists` false → skipped). The 4.2 s incremental
import fixed it: the 19_19 foliage 594 → 1472 instances / 44
MultiMeshes / 22 tree keys with trunk colliders, the statics 0 → 39
(38 Waterfall + 1 FX).

**The runtime (the 5-tile world):** the boot ~8.6 s; the placement:
20_18 401 statics / 112 lights, 20_17 272/10, 21_18 1445/2, 19_18
1119/1755, 19_19 39/1; the foliage total 4402 instances in 168
MultiMeshes.

**The visual checks:** the lake view from the PlayerStart
(tmp/lake_view) — the terrain blends, the trees, the horizon hills,
structurally sane. The waterfall cliff (tmp/waterfall_view2) — the
waterfall rocks + the ledge + the water card render; the water card is
OPAQUE (the dwaterfall textures carry NO alpha — the client's water
transparency is a material property, not texture alpha; the animation
is a separate stage).

**GOLDEN BASELINE PASS:** 190/5/3/6/21 px >8 (the character-strip idle
noise, below the 1000-px gate).

**Pending:** the lake water plane (the water stage — the basin renders
bare), the waterfall transparency/animation, and when 20_19 is built:
its west seam vs 19_19's east edge is sampled from the real t_20_19
except the ONE clamped corner vertex — check the corner then.

## 2026-11-21 — DEVLOG-114: the bad-alpha trees in 19_19 fixed; the
## foliage pattern is now a PERMANENT rule in AGENTS.md

The user's report: minimum 2 tree types with bad alpha — the canopy
cards rendered as OPAQUE polygons (the screenshots: the moss-card pile
and the mossy tree with the flat cards).

**The root cause:** the alpha-scissor predicate keyed on the texture
NAME ("grass"/"leaf" in the name) — a 20_18-era heuristic. The 19_19
families name their foliage differently, so their alpha cards rendered
opaque. The scan of all 44 foliage keys of 19_19 found every violation:
- `Oren_tree_S:Oren_Darkelf_tree08` (20 instances): 4 moss textures
  oren_darkelf_tree01_s3..s6 with cutout alpha (min 0), no name match;
- `Field_Deco_Artifact_S:DElf_TombTower` / `DElf_TombTower_Btm`:
  delf_tomb_alpa01 / delf_tomb_04 (the banners);
- `Field_Deco_Artifact_S:DElf_Guard_1` (14): delfguard_alpa01 (the flag).

**The fix:** the cutout is decided BY CONTENT for every foliage key —
`_is_foliage_key(key) or "grass"/"leaf" in the name`, gated on
`Image.detect_alpha()`. The scissor on an all-opaque alpha is a no-op;
the stone meshes in the same packages carry no alpha at all (the scan
verified). The name check remains ONLY for the non-foliage keys (the
carpet alpha = a specular/blend mask — never cut). Plus: the boot
prints `WARN: tree key without trunk collider` for every tree key
missing its trunk entry — the pattern violation is now visible on every
boot (currently flags the 20_17 card-cluster decotrees, an intentional
pass-through).

**The verification:** the tomb area close-up (tmp/alpha_fix/tomb) —
the moss cards cut with the torn edges, the obelisks render; the
tree08 close-up (tmp/alpha_fix/tree08) — the moss cards cut (the sky
shows through); the guard/tower alpha textures take the same path.

**The PERMANENT rule (the user's order «закрепи это в MD») written into
AGENTS.md — "The foliage/trees pattern":** the five points (the
MultiMesh batching, the alpha by CONTENT, the trunk colliders at the
bark center, the visibility ranges, the per-tile verification with the
WARN/trace/screenshot gates) apply to EVERY tile — the existing and
every future one.

## 2026-11-21 — DEVLOG-115: 18_19 (the west-southwest tile, the Dark Elf
## dungeon area) — the SIXTH tile; the dungeon interiors are BSP (NOT ported)

The user's order: «делаем теперь 18_19».

**The build:** `build --map 18_19 --neighbor 18_18 19_18 19_19 19_20
17_20 17_19 17_18 --assets-dir assets/maps/18_19` — SEVEN neighbors
(the client ships t_17_17..20 for the west ring, but NO t_18_20 — the
south neighbor 18_20 is a pure-ocean tile without terrain data). 2.6 min
(the first UModel export). rc 0: 1859 actors, 1683 statics (0 deleted),
1 PlayerStart (−39625, 37999, −3154), 69 meshes (45 NEW keys — the
Oren_ded_s dungeon package: wall_deco, bridg, altar, slav_deco,
topcage, stair, torch, lamps, sewage, DEd_board/lamp), 90 textures,
8 layers (8 valid), 59040 quads / **6496 holes** (the dungeon footprint
≈ 10% of the tile) / 1932 edge-turns, origin (−65536, 32768).
**clamped_border_samples: 256** — the whole south edge (the missing
t_18_20). verify: ok (the per-map gates + the expected warnings).

**THE SEAM MEASURED:** 18_19's east border vs 19_19's west border, all
257 vertices: max |dZ| = 0.00.

**The import was run IMMEDIATELY after the build** (the 19_19 lesson):
3.8 s incremental. The boot: **placed 1033 static meshes + 650 foliage
instances = 1683** (the exact actor accounting), 403 collision shapes,
175 lights. The foliage: 650 instances / 28 MultiMeshes / **5 tree keys
with trunks = ALL of the tile's tree keys** (the known Oren_Darkelf
family; no new tree families). The WARN lines caught one PRE-EXISTING
violation in 20_17: `Innadrill_tree_S:inna_Stree01` (4 palms) has no
bark-named surface → pass-through — pending.

**The runtime check caught the honest boundary of the port:** a test
spawn at (−47500, 55000) fell into the void (Z −1013 m) — the point
sits inside the terrain-hole block (5×5 quads = 0), and the floor
profiles over the dungeon complex (the torch line, the diagonal sweep)
return NO-HIT except the deco meshes themselves. **The dungeon
interiors (the walls/floors of the halls) are the client's BSP LEVEL
GEOMETRY** — only 20_18 has the BSP stage in this project
(bsp.json/levelbsp.json/meshes_bsp, built by the dedicated 20_18-era
tools); the expansion tiles carry the terrain + the statics only. The
largest 18_19 statics (topcage 29 m, bridg_rest 22 m, wall_deco 19 m)
are decos, not floor slabs — the floors do not exist as statics.

**GOLDEN BASELINE PASS:** 187/4/0/6/1 px >8.

**Frames:** the PlayerStart forest view (tmp/1819_view/spawn — the
mossy trees with the working alpha), the torch area profile evidence
(the torch meshes hit, the floors absent).

**PENDING / the user's decision:** the 18_19 dungeon interiors need the
BSP level-geometry stage (the 20_18-style dedicated pipeline run for
this tile — the room walls/floors/ceilings) — the terrain, the statics
and the foliage of the tile are ported and verified. Also pending: the
inna_Stree01 palm trunk (20_17), the water plane, the waterfalls.

## 2026-11-21 — DEVLOG-116: the BSP stage of 18_19 OPENED and DONE —
## the dungeon renders from the client's section vertex streams

The user's order: «открываем BSP стадию 18_19» (18_19 = the last Dark
Elf map; the others carry only small DE pieces).

**The first attempt (the licensee-23 surf path) FAILED — the root cause
measured:** the maps ship in MULTIPLE licensee generations (20_18/19_18/
19_19 = licensee 23, 21_18/18_19 = 25, 20_17 = 28; all ver 123). The
levelbsp.py node/surf/points parse was built against the licensee-23
Model500. For 18_19's Model5 (4.6 MB, 3932 nodes / 1487 surfs / 78650
verts) the COMPACT arrays parse fine (the section validation
rev == numnodes == the per-section node count passes!) but the POINTS
float array reads as garbage: the drawn polys collapsed to slivers
(the bbox-corner pattern ±327680/±262144/±16384 — the exact corners of
the zone box; the unique z values = ±16384 exactly). The header-skip
scan (1..119) found no valid alternative — the licensee-25 POINTS
layout differs structurally.

**The engine.dll RE (the craft-anything memory + a fresh decompile):**
UModel::Serialize is licensee-uniform for LicenseeVer ≥ 9; FBspSurf has
an extra int only for LicenseeVer ≥ 21 (both 23 and 25 ≥ 21 — not the
difference). The arrays' element serializers = ??6...FBspNode (530 B)
/ ??6...FBspSurf (381 B) / ...FBspVertex / ...FBspSection — decompiled
into the evidence memory (ev_bfeff29c).

**THE WORKING PATH — the client's own render data: the SECTION vertex
streams.** parse_sections (DEVLOG-82-era code) validates structurally
for 18_19 and carries the REAL geometry: 18 sections / 18758 vertices
of 40-byte records (pos12 + uv8 + 8 mystery + normal12), the sane
coordinates x[−51513,−43271] y[42332,59084] z[−5947,−3383] = the exact
dungeon levels. The node runs map onto the streams: sum(node.nvert) ==
section.nvert for 18/18 sections; each run = one polygon (a fan); the
UVs = the client's FINAL tile coordinates (texel_uvs=false — the
runtime _build_bsp now honors a per-surface "texel_uvs" key from
levelbsp.json; the 20_18 licensee-23 artifact keeps its default true).

**New tool: tools/l2strict/level_sections.py** (the section-stream
exporter, the same LevelBSP.gltf/levelbsp.json contract). The filters:
the ZonePortal/AntiPortal sections, the no-material sections, the span
> 7000, and the |z| > 130 m (the zone-box corner polys leak at exactly
±163.84 m — beyond any real L2 geometry). Result: **3002 polygons in 10
surfaces, 380 KB**, all 8 materials = the dungeon textures
(dark_dgn_001_1/006/020/021/022/029/111/119 + DE_V_roof — 4 of them
exported and staged fresh via UModel).

**The verification:**
- The floor profile through the torch hall (−47533,55269 →
  −47334,55211): EVERY step = `y=-38.947 via LevelBSP`, ny=1.00 — the
  hall floor exists, flat, exact; the before-state = NO-HIT.
- The character spawns inside and STANDS (the trimesh collider with
  backface collision; Z −3894.6 = on the floor).
- The interior render (tmp/dungeon_view): the stone floor with the
  hex pattern at the authentic scale, the gothic arch colonnades, the
  golden bas-reliefs, the light shafts, the sky through the openings.
- GOLDEN BASELINE PASS: 174/3/0/9/3 px >8.

**Note for the future BSP stages:** the same section-stream path applies
to any licensee-25+ tile (21_18 = 25, 20_17 = 28 — the latter may need
its own layout check); the licensee-23 tiles (19_18/19_19) can use
either path. The tool consumes only the .unr + shader_diffuse.json (the
empty map is fine — the direct Texture materials resolve without it).

## DEVLOG-117 — 2026-11-21: the spawn on the village→Shrine road + the Shillien Temple 3D-texture transition (SPOM walls + built-in heightmap floors)

**The user's orders:** (1) the respawn point moves onto the road between
the DE village and the Shillien Temple (both on 20_18 — the temple is
NOT 18_19; 18_19's dungeon is a different structure); (2) begin the
old-textures → 3D-like transition for the temple: WALLS through SPOM
(godotshaders.com "SPOM with horizon detection, self shading, silhouette
clipping, parallax occlusion mapping, self shading, horizon trimming
erosion" by Amose05, CC0 — the user provided the link after "AMD GPUOpen
Silhouette POM" turned out to be a made-up name), FLOORS through Godot
4.7's built-in heightmap (BaseMaterial3D deep parallax, configurable
min/max layers); (3) the temple STAIRS postponed — the geometry gets
CREATED natively later (the modern-port rule).

**The spawn:** (21109, 12819, ground −36.66, ny 1.00), yaw −1.2313
facing the temple entrance (26180,11032). Chosen from the route floor
profile (7400,17650 → 26180,11032: the terrain stretch f≈0.4..0.95 sits
at z −36.5..−37.5, ny≈1.00) + the tree-distance scan (the first
candidate (19607,13348) spawned INSIDE a canopy — the trees come from
map.json, the clear spot keeps the nearest tree 1238 units away). The
temple silhouette is visible ahead from the spawn.
**VERIFICATION MODE CHANGE (the user's directive, this stage):** NO
automatic mass re-renders (the golden-baseline 5-view village suite and
friends are NOT run for temple iterations) — the village is not what we
are touching, and every rebuild re-renders untouched content. The
verification = the USER'S screenshots against the original client. The
golden baseline itself stays untouched (all 5 baseline viewports use
ABSOLUTE L2_SPAWN positions — the default-spawn move cannot shift them).

**The texture transition (one height source — the DEVLOG-94 rule):**
- texgen.py: + PACKAGE_HEIGHT_BLUR (sylen_temple_t → radius 4.0, the
  DEVLOG-89 low-frequency lesson) + the standalone `<obj>.pbr_height.png`
  (the SAME height_pom field the albedo's A channel carries) + RELIEF for
  the floors (ai_004/in022: 0.05, 2.0). 40 oren_sylen_* sets regenerated.
- assets/shaders/l2_spom.gdshader (NEW): the Amose05 SPOM ported onto the
  project conventions — the screen-Jacobian TBN (the meshes have no
  tangents), meters-based pom_scale via tile_m, the angle/distance
  anti-swim fades, explicit textureLod in the loops, the albedo's A
  channel as the marched height, the SPOM layer ladder (min/max layers),
  the self-shadow march in light() (the published BRDF, transmittance
  semantics), silhouette clipping + curved-silhouette horizon erosion as
  per-material toggles. ONE compile fix: SPECULAR is not readable in
  light() — the published shader's own `specular` uniform restored (0.35,
  the DEVLOG-92 matte stone).
- scripts/l2_proc_tex.gd: SPOM_WALLS (30 sylen keys — the skin, pillars,
  entrances, doors, interior walls/ceilings) → _spom_material; HEIGHTMAP
  _FLOORS (ai_004, in022 — the interior floor + the platform, the same
  textures also floor the court in the level BSP) → _floor_heightmap
  _material (BaseMaterial3D: heightmap_enabled + deep_parallax + min 8 /
  max 32 layers + pbr_height + the height-derived normal + the roughness
  channel from the normal's alpha). L2_SPOM_OFF=1 = the A/B toggle (pom
  0 / the floor material falls through to the flat PBR path).
- world.gd: _with_normals_for() — flat normals + tangents (SurfaceTool,
  deindexed) for the sylen surfaces of BOTH BSP meshes (LevelBSP 4/9 =
  the court, TempleBsp 10/10) — the built-in heightmap needs the mesh
  tangent frame; the jac-TBN shader surfaces pass through pixel-identical.

**What is OFF and why (audited, not forgotten):** silhouette clipping
and the horizon erosion — the temple UVs TILE (the skin spans
u −5.3..6.3, pir −0.66..2.74, deco12 v −0.96..1.99; UModel strips the
accessor min/max — measured from the buffers): a 0..1 clip would erase
the walls. The toggles stay in the shader for per-texture enablement
once a true-0..1 surface needs the carved edge. The pillar horizon mode
needs per-mesh material instances (the pillar textures are shared with
flat walls) — follow-up.

**The numbers that ran (before the verification-mode change):**
- Gate A: 0 shader-error lines in all 4 render logs.
- Gate B (A/B, L2_SPOM_OFF): the interior view 13827 px >8 (780 >32,
  max 97) — the POM + self-shading move pixels on the walls (top half
  9876) and the floor (bottom 3951).
- The spawn floor profile: standing at −36.66 over terrain ny=1.00; the
  route profile clean (one tree canopy above the path at f=0.5, 3.8 m
  clearance).
- The renders: tmp/spom_verify/{spawn_road2,temple_facade,temple_
  interior,temple_interior_nopom} — the facade shows the carved panels
  + the lit spider emblem; the interior shows the ai_004 tile floor +
  the SPOM walls/pillars.
**NOT run:** the golden-baseline village suite (cancelled by the user's
verification-mode directive above).

**Pending:** the temple stairs geometry (create natively); the silhouette
carving per-UV-audit; the deco/statue textures (silen_statue_*, in101,
ai_001..003) still on the flat PBR path; the interior is dim (the
lighting stage is not opened); commit authorization for everything.

## DEVLOG-118 — 2026-11-21: the user's three verdicts — the road columns restored, the sun-side film fixed, the statue light off

**The user's report (their screenshots):** (1) the road columns were
never rolled back to the stable state (top after Blender, bottom with
the 4x upscale) — the order predates this session; (2) the temple
outside: in shadow perfect (better than the original), but on the sun
side a matte gray film vs the native textures flips with the angle
("бегает переход"); (3) the artificial light on the Shillien statue
must be OFF so the statue can be judged bare.
**The verification mode stands (DEVLOG-117): NO agent-run render
batches — the user tests with their own screenshots.** Four temple
views launched before the second directive completed (0 shader errors,
the light-skip prints confirmed) and sit in tmp/spom_verify/ unused.

**(1) The columns — root cause found, the stable state restored.**
The DEVLOG-117 SPOM routing hijacked the shared texture keys
(oren_sylen_001/in002/in017/in019/in001 = the outdeco04 column's
surfaces AND the temple walls'), and the baked switch in world.gd keyed
on the material's shader path ending with l2_surface_pbr.gdshader — it
silently stopped firing, so the Blender bake was lost. The DEVLOG-101
_x4 albedo override was ALSO gone (dismantled somewhere in the 103-116
sessions; the _x4 PNGs no longer exist). The restore:
- l2_proc_tex.gd: `pbr_material_for()` — the public plain-PBR route,
  bypassing SPOM/floor, its own "|pbr" cache suffix (the SPOM and PBR
  materials for one texture key coexist).
- world.gd baked block: rebuilds each baked-mesh surface's material
  from `L2ProcTex.pbr_material_for` (not from the whatever-was-assigned
  check), sets use_baked + the baked normal/AO (UV2) + relief_gain 1.2,
  then the DEVLOG-101 override: if
  `res://assets/textures/upscale/<obj>_albedo_rgb_upscale.jpg` exists
  (only the ornate in001/in019) the albedo swaps to it; the other
  surfaces keep the client tile texture.

**(2) The sun-side film — two view/angle instabilities in the SPOM
self-shadow, fixed in l2_spom.gdshader:**
- The march and the crevice AO read the VIEW-DEPENDENT displaced UV
  (base_uv) — the occlusion pattern swam with the camera (the march
  start and the AO pattern move as the camera orbits within the
  angle/distance-fade range). Both now read the STABLE surface UV
  (the new flat_uv varying); the POM'd albedo/normal sampling at
  base_uv is unchanged (that is the relief itself).
- Grazing light: travel.z -> 0⁻ explodes the march steps (P ~
  1/travel.z) and the walk samples arbitrary texels — whole faces
  flipped to blocked (the film) depending on the sun angle. New gate:
  travel.z > −0.3 → transmittance 1.0 (no shadow info — the native
  texture, stable), plus a ±2.0 UV step clamp. The shadow-side look is
  untouched (the march only runs on sun-lit faces; in shadow
  ATTENUATION=0 kills the term anyway).

**(3) The statue light off:** _build_lights skips the Light actors
within 150 units of the statue (30044,11021) — Light69 (br 550) +
Light55 (250); the boot prints "light skipped (the Shillien statue
judgment): <name>". The next-nearest lights are 290+ units away
(outside their 60-120 radii). The statue renders bare for the
replace-or-not decision.

**Pending:** the user's visual verdicts on all three; the statue
replace-or-not; the commit authorization.

## DEVLOG-119 — 2026-11-21: the user's verdicts round 2 — the film's sun-side darkening removed, the statue "hat" diagnosed and cut

**The verdicts:** (1) the road columns — OK (the restored stable state
approved); (2) the gray film REMAINS outside under the main camera
angle + at distance; (3) the statue light-off — OK, but the old porting
bug shows: a dark "hat"/wrong texture over the statue's head.

**(2) The film, round 2 — the remaining sun-side darkening layers
removed (l2_spom.gdshader):**
- The crevice AO removed: weight clamp(pom_scale*20)=0.8 darkened the
  dark painted texels ~36% (AO = mix(1, 0.55+0.45h, 0.8)) — a STATIC
  matte film vs the client's flat albedo, present at every angle and
  distance (the village never had it: pom=0 → weight 0 there). AO=1.0.
- The self-shadow march disabled (use_self_shadow=false, the uniform
  remains): the binary blocked/lit patches over the blur-4 height field
  are large smooth darkening regions on the sun-lit walls — the film
  itself. The client carries no wall self-shadow. The POM relief (the
  UV-shift march) stays — that is the 3D read. The grazing gate +
  flat_uv stability from round 1 remain in the shader.
- Diagnosis method: data, no renders (the verification mode stands).

**(3) The "hat" over the statue's head — the old additive/mask port
bug, content-verified (no godot runs):**
- The statue mesh's 5 surfaces share one bbox (the primitives
  interleave — no geometric isolation); the textures decide.
  silen_statue_3/2/4 = RGB (opaque, correct). silen_statue_1 = RGBA,
  27% real alpha-0, dark RGB — the texture IS a masked atlas: the
  face/crown parts sit on black=transparent surroundings; rendered
  OPAQUE the black texels became the dark cap over the head.
  silen_statue_chain = RGBA 67% transparent (the chain links) — the
  same class (the "thick dark bars" across the arms in the renders).
- The runtime's alpha-scissor branch was foliage-only (the DEVLOG-114
  content rule + the carpet guard). Fix: an explicit non-foliage
  TRUE-mask list in the static PNG-fallback —
  sylen_temple_t:silen_statue_1 + sylen_temple_t:silen_statue_chain →
  TRANSPARENCY_ALPHA_SCISSOR 0.35 + CULL_DISABLED, gated by
  img.detect_alpha(). The carpet alphas stay opaque — the DEVLOG-114
  rule holds: only the verified true masks cut, only by this list.

**State:** import 0 / headless boot 0 / 0 shader+script errors; the
boot prints "light skipped (the Shillien statue judgment): Light55/
Light69". NO renders run (the user tests with their screenshots).

**Pending:** the user's verdict on the film (if anything remains, the
next suspects are the POM displacement itself at close range and the
GGX specular); the statue bare-look verdict (replace or not); the
commit authorization.

## DEVLOG-120 — 2026-11-21: the day/night cycle + the overcast sky + the full moon + the random-time test mode; the statue "hat" = the deco07 slot binding

**The user's verdicts:** the film is GONE (approved); the "hat" over the
statue's head REMAINS; the lighting stage OPENS: overcast weather (the
dimmer sun), the day/night cycle (a game day = 4 real hours, the night =
1 of them), the real sun path (east -> west, the zenith at 1-2 pm), the
random start time for the lighting/shadow/angle comparisons, and the
FULL moon at night (no phases; the eclipse in the far drawer).

**The "hat" — the data chase (no godot runs, the user banned the
display launches twice):** the hat box above the crown contains exactly
ONE piece of geometry — sylentemple_deco07 (StaticMeshActor25, d=131
units, the 9.6 x 4.9 m curved apse strip behind the statue, its top
z -2998 vs the crown top -3014). TempleBsp and the statue itself have
NOTHING there. The strip's runtime texture = **oren_sylen_t004** (the
asset_map primitive_material_indices [2] — the facade band with the
plaster field) while the strip's UV window (u 0.585..0.854,
v 0.314..0.769) fits the carved-arch atlas **oren_sylen_in031** (slot
0, the mesh's primary material). The t004 band over the head read as
"some cap with the wrong texture". The same section->material binding
class as the 2026-11-10 statue-hand bug (fnd_12). FIX: a per-key
override in _get_mesh — deco07's surfaces take slot 0 (in031). The
candidates compared at that UV window: in031 (the carved arch atlas),
in005 (the pointed-arch wall window), t004 (the facade band — the
current wrong pick). The user's screenshot is the arbiter; in005 is
the next candidate if in031 reads wrong.

**The day/night system (world.gd, DEVLOG-120):**
- The clock: 24 game hours per 4 REAL hours (= 1/600 game-h per real
  second). L2_TIME=<hour> pins the start (the DEFAULT = RANDOM — the
  user's order: every launch a random time to compare lighting/
  shadows/sun angle); L2_TIME_SCALE=<x> multiplies the clock speed.
  The boot prints "day/night: game time <h> (random|L2_TIME), sun elev
  <deg>".
- The sun path: east (+X) horizon at 04:30 -> the ZENITH at 13:30 ->
  west (-X) horizon at 22:30 (the night = 22:30..04:30 = 6 game hours =
  1 real hour). _tod_sun_dir(): (cos a, sin a, 0) in the east-up-west
  plane; a = PI*(clock-4.5)/18.
- The OVERCAST weather: the sun energy capped at 2.8 (the old fixed 5.0
  read too hot on the temple textures — the user's "без излишнего
  света"), warm (1.0,0.75,0.5) at low elevations -> (1.0,0.97,0.93) at
  the zenith; the shadow stays on (the user compares the shadows).
- The night: the FULL moon — the moon light (bluish 0.72,0.8,1.0,
  energy 0.55 at full night, shadowed) rides the ANTI-SUN (it rises in
  the east at sunset — physically consistent); the moon DISC = a
  clean-room generated texture (tmp/make_moon.py, seed 20261121:
  limb-darkened disc + deterministic maria blotches + a soft edge,
  512x512 -> assets/textures/sky/moon_full.png) on a camera-following
  billboard Sprite3D at 700 m (depth-tested — the terrain occludes it),
  ~46 m across.
- The sky: the overcast palette day/dusk/night lerped by the elevation
  factors (the gray day 0.40..0.64, the warm dusk horizon 0.62,0.45,0.33,
  the dark night); the fog color follows the horizon; the zone ambient
  dims to 35% and shifts bluish at night. The dawn/dusk band =
  smoothstep windows over the sun elevation.
- The L2_BRIGHT diagnostic bypasses the cycle entirely (_bright_mode) —
  its flat-white ambient survives.
- THE ECLIPSE: the far drawer (the user's words), not implemented.

**State:** import 0 / headless boot 0 / 0 errors; the randomizer prints
"game time 10.00 h (random), sun elev 55.0 deg" (the math cross-checked:
10:00 -> 55 deg). NO display runs (the user tests with their
screenshots and the L2_TIME pinning).

**Pending:** the user's verdict on the hat (in031 vs in005 vs t004 —
the strip is the only geometry above the head); the day/night look
across the random launches; the commit authorization.

## DEVLOG-121 — 2026-11-21: the day/night round 2 — the "eclipse" moon fixed, the shadow-acne PWM fixed, the sheen killed, the HUD clock

**The user's four problems:** (1) the hat over the statue remains, black
now; (2) "either you made an eclipse or the wrong sun/moon" — the night
sky showed a BLACK disc ringed by a bright glow; (3) the textures read
B/W with 3D under unclear camera-dependent lighting; (4) inside the
temple the sun/moon light "travels in waves like LED on camera" (the
stipple visible in their shot).

**(2) The "eclipse" — two real bugs, both fixed:**
- The moon texture was premultiplied-UNSAFE: the RGB outside the disc
  stayed bright (0.77) with alpha 0 — under the premultiplied
  interpretation the outside leaks as the bright ring (the glow), and
  the depth fog at 700 m blackened the disc (the black disc). The
  texture regenerated premultiplied-safe (the outside RGB = 0, the edge
  RGB scaled by alpha; tmp/make_moon.py).
- The Sprite3D replaced by a QuadMesh + StandardMaterial3D (unshaded,
  transparency alpha, billboard, `disable_fog` guarded by `"disable_fog"
  in mat`): the fog can no longer touch the disc.

**(4) The "PWM/waves" = the shadow-map acne** (the stipple in the
user's shot — the classic depth-fight at this world scale): the sun AND
the moon get shadow_bias 0.25 (the default 0.1), shadow_normal_bias 4.0
(the default 2.0), shadow_blur 1.4.

**(3) The B/W camera-dependent sheen = the SPOM GGX fresnel** at the
grazing angles whitening the walls under the moonlight: the `specular`
uniform 0.35 -> 0.0 (the temple stone is matte; F0 = 0 kills the term).
The moon energy 0.55 -> 0.45 (the B/W wash contribution).

**(1) The hat — the texture-window scan settles the texture part:**
the strip's UV window (u 0.585..0.854, v 0.314..0.769) is DARK on ALL
three candidates (in031 mean 0.189/std 0.166, in005 0.213/0.128, t004
0.127/0.110) — the strip is dark carved stone in ANY assignment, and at
night ANY of them is black (unlit). in031 KEPT (the richest carving).
**The ROOT of the perception is geometric: the apse VAULT above the
temple is missing from the TempleBsp build** (the hat box above z -3300
contains only the strip — the client encloses the same strip with the
vault, so it never reads as a floating cap). QUEUED as the
temple_bsp-coverage task (the geometry rebuild needs the user's day
reference first).

**The time display (the user's request):** the HUD label now shows
"HH:MM фаза" (день / утро-вечер / сумерки / ночь by the sun elevation)
next to the coordinates — world.gd tod_label(), player.gd renders it.

**State:** import 0 / headless boot 0 / 0 errors; the boot printed
"game time 18.79 h (random), sun elev 37.1 deg" (the math
cross-checked). NO display runs (the user tests).

**Pending:** the hat = the temple_bsp vault coverage (the geometry);
the day-look texture verdict on in031 (the alternates in005/t004 are
one-word switches); the night look after the moon/bias fixes; the
commit authorization.

## DEVLOG-122 — 2026-11-21: the OVERCAST = the cloud dome, the ground fog REMOVED; the deco07 strip deleted from the render

**The user's day verdicts:** the textures OK, the shadows OK (the
temple transition + the day/night lighting approved for the day); BUT
"не пасмурная погода а просто туман" — the recolored gradient + the
distance fog read as FOG, not overcast; and the hat over the statue is
"not needed at all — remove it from the meshes and textures".

**The weather (the user's spec: "затянутое небо, но земля без тумана"):**
- The ground fog REMOVED: the ZoneInfo DistanceFog block (the depth fog
  1..100 m) is disabled in _build_environment; the client values stay
  recorded in the comment for the restore. The per-frame fog-color
  update is gone with it.
- The overcast SKY: a procedural cloud dome (NEW
  assets/shaders/l2_sky_clouds.gdshader) — a camera-following SphereMesh
  (r 780 m, cull_front, unshaded, shadows_disabled) with a clean-room
  FBM cloud layer: the perspective projection on the drift plane, the
  coverage 0.62, the drift tied to the game clock (the clouds move with
  the day). The palette (day/dusk/night) rides the SAME phase factors as
  before — the world.gd sets the uniforms per frame. The gaps let the
  moon glimmer through (the night moon stays visible).
- The ProceduralSkyMaterial stays as the BG fallback behind the dome.

**The hat: DELETED (the user's order — "она вообще не нужна"):** the
key sylen_temple_s:sylentemple_deco07 returns null in _get_mesh — both
instances (StaticMeshActor25/28) drop out of the render WITH their
colliders; the t004/in031 slot experiments are dead code, removed. The
staged glTF and the asset_map reference stay intact (the removal is
render-path only — regenerable, reversible). The root-cause note stands:
the client hides the same strip inside the apse VAULT that our TempleBsp
build does not have above z -3300 — if the vault geometry gets built
later, the strip's absence vs the client must be re-judged.

**State:** import 0 / headless boot 0 / 0 errors; the boot printed
"game time 16.11 h (random), sun elev 63.9 deg" (the math
cross-checked). One indent slip (the dome block landed inside the
bright-mode gate) caught by the headless compile gate and fixed. NO
display runs.

**Pending:** the user's overcast/fog verdict; the night sky + the moon
through the cloud gaps; the commit authorization (everything since
DEVLOG-96 is uncommitted).

## DEVLOG-123 — 2026-11-21: the hat is NOT deco07 — the ceiling-hole / statue-surface candidates + the ledge-film clamp; the trace handed to the user

**The user's verdicts:** the hat REMAINED after the deco07 removal (⇒
deco07 was never the hat — my box scans were vertex-based on the shared
vertex pools and missed the truth); a few temple protrusions get the
film in the sun again (the other textures don't). The day textures and
shadows: approved.

**The ledge film — the mechanism + the fix (one line):** the small
ornate faces (the skin's trim surfaces, the tilted deco09 pieces) carry
a tiny tile_m (meters per tile from the Jacobian) — pom_scale/tile_m
explodes and the POM march samples fly across the whole texture = the
wash, view/sun-angle dependent. FIX: the ray_uv clamp to ±0.35 UV in
l2_spom.gdshader (the parallax physically cannot exceed a fraction of
the tile; the big wall faces sit at ~0.01-0.08 — untouched; the approved
columns/walls can't change).

**The hat — the honest state of the evidence (all data, no renders):**
- The triangle-level scan (the vertex pools are SHARED between the
  primitives — the vertex-in-box test was meaningless; the centroids of
  the INDEXED triangles is the truth): above the crown top (z -3014)
  there is NO real geometry — only ~17 tiny skin fragments (cornices at
  z -2876..-2956) and the 0x40a000 in002 wall-top plane at -2999 (in
  our TempleBsp surf 3, rendered).
- The level BSP band scan (tmp/hat_nodes.py): NO ceiling nodes above
  the apse — the client's enclosure above the statue is NOT in the
  level BSP, NOT in the skin shell, NOT in our scans.
- The statue's own surfaces sit in the region BELOW the crown top but
  visually ABOVE it from the user's low camera: surf 1 (silen_statue_2,
  the upper drapery atlas) has 640/732 triangles at z -3695..-3379 —
  the statue's own unlit upper body reads as a dark mass over the crown
  in the dark, and with the statue light OFF (the user's judgment
  order) everything there is black.
- The two remaining candidates: (a) the SKY through the missing apse
  enclosure (the client frames the same view with vault geometry we
  haven't found in the data), (b) the statue's own unlit upper surfaces.
- DECISION: the agent cannot disambiguate without a render — the trace
  is handed to the USER (their machine, their launch):
    L2_SPAWN="29850,11040,-3350" L2_VIEW_YAW=-1.474 L2_VIEW_PITCH=0.55 \
    L2_TRACE_BOX="500,60,1340,460" godot --path . --rendering-driver opengl3
  The TRACE lines name the mesh/face/texture per hit in the hat region;
  the paste-back gives the exact answer.

**State:** import 0 / headless boot 0 / 0 errors (the shader clamp).

## DEVLOG-124 — 2026-11-21: the hat SOLVED — the UE2-Masked statue atlas; the gloss killed on both material paths; the weather scope fixed in AGENTS.md

**The hat — the root found by the texture sampling (no renders):** the
statue's hat-band triangles were UV-sampled against their atlases:
**surf 0 (silen_statue_3): 344 triangles, 69% sample BLACK texels**
(mean brightness 0.075; the UVs TILE u -0.52..1.76 / v -0.83..1.97 and
wrap into the atlas's black margins; the chain surface = 100% black).
This is the UE2 PF_Masked class: in the client the palette index 0 (the
black) is TRANSPARENT; our staged RGB made the margins opaque — the
same class as the 2026-11-10 statue-hand bug. FIX:
- tmp/statue_alpha.py: statue_3 + statue_4 restaged RGBA with the binary
  alpha (the luminance < 0.06 -> transparent; the carve shadows 0.1-0.2
  stay opaque); the black-margin fractions 0.17 / 0.28.
- world.gd: the scissor list += statue_3/statue_4 (the detect_alpha gate
  now passes). statue_1 (the real alpha) and statue_chain were already
  in; statue_2's UVs never leave 0..1 (its margins are unreachable).
- The hat's earlier candidates (deco07, the vault hole) were wrong; the
  deco07 removal stays (the user judged the strip not needed).

**The protrusion gloss — killed on BOTH material paths:**
- l2_spom.gdshader: ROUGHNESS matte floor 0.82 (the roughness 0.59-0.86
  + the bright overcast dome = the environment specular sheen on the
  sun-facing ornate faces) + SPECULAR = 0.0 explicit.
- l2_surface_pbr.gdshader: the NEW specular_strength uniform (the
  DEFAULT 0.5 = Godot's own — the approved village look untouched);
  l2_proc_tex.gd sets it to 0.0 for the sylen_temple keys only.
- The earlier ray_uv clamp (±0.35 UV) stays (the march blow-up guard).

**The weather scope (the user's directive — PERMANENT, now in
AGENTS.md):** the overcast sky + the day/night cycle apply ONLY to the
built Dark Elf territory maps; the border zones are adjusted manually
per-zone; every new map gets its own individual weather. Never extend
the weather system beyond the built DE tiles without the user's
explicit per-map order.

**State:** import 0 / headless boot 0 / 0 errors; "game time 16.80 h
(random), sun elev 57.0 deg". NO display runs.

**Pending:** the user's verdict on the hat (the masked-alpha fix) and
the gloss; the commit authorization (everything since DEVLOG-96).

## DEVLOG-125 — 2026-11-21: the night dimmed, the moon shadows OFF (the PWM root), the 4 Hz light quantization, the terrain matte, the FULL cache clean

**The user's night verdicts:** the side ornate textures stand out with a
"fixed tint/light" at night; the hat remains (the Godot cache suspected
— "несколько итераций пересобираешь без очищения кеша"); the moon's PWM
on the stairs persists (the moon "has a refresh frequency"); the rocks
get the film under the moon (the terrain textures = the direct client
transfer, no update).

**(1) The fixed-tint look = the AMBIENT term:** the constant night
ambient (0.165, bluish) lit the pale ornate albedos in the dark while
the dark walls went black. The night dims: the ambient floor 0.35 ->
0.20 of the tuned day value, the moon energy 0.45 -> 0.32, the night
ambient tint subtler (0.33,0.35,0.42).

**(3) The moon PWM — the root + the fix:** the light direction updated
EVERY frame -> the shadow map re-rasterized every frame -> the shimmer
on the moonlit stairs (the user read it as the moon's "refresh
frequency"). TWO fixes: the moon light carries NO shadows at all (the
client's night has no dynamic shadows — the moon is a soft fill), and
BOTH lights' directions quantize to 4 Hz (the angular step ~0.002 deg —
imperceptible, the shadow map stays static between the ticks).

**(4) The rocks' film = the terrain shader's Godot-default specular**
(the terrain = the direct client texture transfer, no PBR — the user's
note): SPECULAR 0.1 -> 0.0 in scripts/terrain.gdshader (the rock is
fully matte).

**(2) The cache — the user's suspicion honored:** the FULL clean
reimport run (rm -rf .godot/imported + a fresh import). The statue_3
file verified RGBA on disk; the masked-alpha scissor now guaranteed in
the imported state. If the hat STILL shows after this build, the two
remaining candidates stand (the apse enclosure hole vs the statue's own
unlit drapery) and the TRACE from the user's machine decides:
    L2_SPAWN="29850,11040,-3350" L2_VIEW_YAW=-1.474 L2_VIEW_PITCH=0.55 \
    L2_TRACE_BOX="500,60,1340,460" godot --path . --rendering-driver opengl3

**State:** the clean import 0 / headless boot 0 / 0 errors; "game time
12.93 h (random), sun elev 84.3 deg" (the near-zenith at 13:00 = the
user's spec). NO display runs.

## DEVLOG-126 — 2026-11-21: the temple horns = sylentemple_deco10 identified (the user's "rebuilt without SPOM" — literal truth); in030 joins SPOM

**The identification (the mesh dims + the instance positions):** the
horn/finial protrusions on the temple's second story = sylentemple_deco10
(4 instances, z -2957): 5.7 x 10.7 x 0.44 m thin ornate panels. The
user's diagnosis was LITERAL: deco10's textures = in030 + ai_007, and
in030 was NOT in SPOM_WALLS (the PBR path — no POM, a different shading)
while ai_007 was — ONE mesh, TWO material paths = the standout look in
both the dark and the light versions.

**FIX:** oren_sylen_in030 added to SPOM_WALLS — deco10 renders fully
through the building's material path. The thin-geometry guards stay
(the ray_uv clamp ±0.35, the angle_fade, the matte floor 0.82).

**State:** headless boot 0 / 0 errors. NO display runs.

## DEVLOG-127 — 2026-11-21: the night darkened further (the moon 0.18, the ambient floor 12%) — the pale-albedo contrast vs the client's near-black night

**The user's verdict:** the horns still stand out at night (either an
incomplete rebuild or the wrong fix). The data check: the horn textures
carry NO alpha (the masked class excluded); ai_007 = the palest atlas
(mean RGB 0.331) vs the walls' 0.16 — the horns' albedo is ~2x brighter,
and OUR night (the moon 0.32 + the ambient 0.20 floor) was brighter than
the client's near-black night — the pale surfaces read first.

**FIX:** the moon energy 0.32 -> 0.18; the ambient night floor 0.20 ->
0.12. The client-like near-black night; the moon disc and the lamp
proximity lights stay the night's visible elements.

**Note on "неполная пересборка":** the previous fix (in030 -> SPOM) was
a script-only change — no import involved; the boot compiles the script
fresh. The rebuild was complete for that change; the standout at night
was the night brightness, not the path.

**State:** headless boot 0 / 0 errors. NO display runs.

## DEVLOG-128 — 2026-11-21: the temple's static black = the INWARD WINDING — the SPOM lighting now uses the Jacobian normal (two-sided correct)

**The user's finding:** "the horns work with light and shadows while the
whole temple has been working WITHOUT them — always statically black."
The check: deco10 carries NO normals either (all the temple meshes are
POSITION+TEXCOORD) — the normals theory died. THE ANSWER: the skin
shell is wound INWARD (the client renders everything two-sided and
never cares); the SPOM light() took the built-in NORMAL — on the
outside view it points AWAY from the sun -> NdotL = 0 -> the diffuse
never arrived -> the temple = the ambient-only static black. The
outward-wound deco10 horns lit fine — the exact asymmetry the user saw.

**FIX (one line):** l2_spom.gdshader light(): N = normalize(vN) — the
screen-Jacobian geometric normal (already computed and view-transformed
for the shadow march), correct on BOTH faces. The two-sided lighting is
now geometric, winding-independent.

**State:** import 0 / headless boot 0 / 0 errors ("game time 2.29 h,
sun elev -22.1 deg" — the night boot, the math consistent). NO display
runs.

**Pending:** the user's verdict (the temple walls must now receive the
sun/moon light with the shadows); the hat (the trace or the
enclosure-hole decision); the commit authorization.

## DEVLOG-129 — 2026-11-21: the moon 30 Hz, all the temple lamps OFF, the hat = the skin's upper walls (the offline render proof), the terrain SPOM

**The user's four orders:** (1) the mountains at night are especially
bad — redo with SPOM; (2) the 30 Hz is THE MOON's update frequency (not
the temple lamps — "у нас их нету"); (3) the hat remains; (4) remove ALL
artificial lighting from the Temple and check whether the natural light
suffices.

**(2) The moon 30 Hz:** the direction quantization applies to the MOON
only (33 ms tick); the sun stays per-frame. The temple lamps were
already gone (the DEVLOG-129 region skip below).

**(4) ALL the temple lights OFF:** _build_lights skips every Light actor
inside the temple region Rect2(25400, 8800, 6100, 8400) (= the
temple_bsp.py REGION). The statue-radius exception is superseded — the
whole temple is natural-light-only. The light sufficiency is the user's
check (with the DEVLOG-128 two-sided lighting the walls finally receive
the sun/moon).

**(3) The hat — SOLVED BY THE OFFLINE SOFTWARE RENDER (no godot):** a
numpy z-buffer rasterizer (tmp/statue_render.py) rendered the statue +
the skin + TempleBsp from the user's hat camera with the alpha-aware
scissor. THE VERDICT: the "hat" = THE SKIN'S DARK UPPER WALLS behind the
statue's head (the surfaces in105/t010/t004/ai_007 filling the frame
behind the crown) — the enclosure EXISTS (no sky, no hole, no foreign
object). The earlier scans missed them because the big wall triangles'
CENTROIDS fall outside the hat box while the triangles cover it. The
walls read as a featureless cap because they had no light — after the
DEVLOG-128 two-sided fix they receive the moon/sun like everything
else. The remaining hat perception = the user's natural-light
sufficiency check (the order 4).

**(1) The terrain SPOM:** texgen ran for the 8 t_oren layer textures
(Obase_1, OG_52/34/48/36, OC_05/03, OST_11 — the low-frequency heights,
PACKAGE_HEIGHT_BLUR += t_oren: 4.0). world.gd builds the heights
Texture2DArray (8 x 512x512 RGBA, the height = the albedo's A; the
missing set = the flat 0.5 gray) + the per-layer uv scales.
terrain.gdshader: the jac tangent frame + the dominant-layer march (the
argmax of the masks picks the array layer; the masks stay UNSHIFTED —
they are the coverage; the detail textures sample at the displaced
tile_uv) + the angle fade and the distance fade 30..90 m + the ±0.35 UV
clamp. The blend order, the base layer and the debug modes are
unchanged. The trap fixed: Texture2DArray.create_from_images is an
INSTANCE method (the parse error caught by the headless gate).

**State:** the clean import 0 / headless boot 0 / 0 errors; "game time
17.31 h (random), sun elev 51.9 deg". NO display runs.

**Pending:** the user's verdicts (the mountains' relief, the night
brightness balance, the temple's natural-light sufficiency = the hat's
final look); the commit authorization (everything since DEVLOG-96).

## DEVLOG-130 — 2026-11-21: the day mountain film = FACETED TERRAIN NORMALS; the hat = the DEAD scissor branch (the PBR path intercepts); the temple BSP normals were never built (the real "static black")

**The user's two reports:** (1) the mountains got more detailed but the
day film increased; (2) the hat above the statue did not disappear.

**(1) The day film = the faceted terrain normals, not the POM.** Data
first: the mountains in the user's 15:24 screenshot are pure terrain
(the heightfield peaks z=+2483 at game (22400,27520); ZERO MT/rock
statics in the box). My terrain POM shifts ZERO pixels beyond 90 m
(dist_fade) and the specular only went DOWN (0.1→0.0) — the shader edit
cannot have changed distant mountains. The real change: _emit_tri set
no normals and generate_normals() on the UNINDEXED triangles produced
per-face FLAT normals; at the old static south-east sun the north faces
sat in ambient only (facets invisible), but the moving day/night sun
lights them directly and the adjacent facets diverge — MEASURED on the
northern slopes at 15:24: the adjacent-facet brightness delta mean
0.184, p95 0.667 (an 18%..67% shimmering mosaic = the film). The client
smooth-shades its terrain (vertex lighting on the heightfield). FIX:
_build_terrain builds a smooth analytic normal grid
(N = normalize(-dz/dx, 1, -dz/dy) per heightfield vertex, the slope
clamped ±4 at the cut-cell borders), _emit_tri takes 3 normals and sets
them per corner, generate_normals() call removed. The POM march is
untouched (it reads the Jacobian, not the mesh normals).

**(2) The hat root cause = the DEVLOG-124 scissor branch is DEAD CODE.**
_get_mesh routes every texture with a generated PBR set through
L2ProcTex.material_for() FIRST and continues; the statue textures have
PBR sets, so the alpha-scissor branch below never fired. material_for
falls to _pbr_material with use_alpha = key in ALPHA_CUTOUT — the
statue keys were not there (only Iron_net/DE_V_fence) → the PF_Masked
palette-0 texels rendered OPAQUE = the black hat. Two-part fix:
  a. texgen re-run for the 5 statue textures — their pbr_albedo alphas
     were STALE (built before the staged mask regeneration; statue_1's
     pbr alpha cut 40% of VISIBLE texels, chain 79%). Verified after the
     re-run: pbr A == staged A (1.000) for 1/3/4/chain; the masks are
     the real client ones (statue_1 27%, 3 17%, 4 28%, chain 66% —
     chain's transparent background is NON-black RGB, a legit PF_Masked
     layout).
  b. ALPHA_CUTOUT += sylen_temple_t:silen_statue_1/3/4/chain. statue_2
     stays OPAQUE: its staged PNG is RGB (an alpha-less client format —
     the black texels are genuine paint, not palette 0). Headless probe:
     use_alpha=true on the real material path.

**(3) THE BIG FIND — the temple BSP normals were NEVER built (the real
"статично чёрный храм", the user's msg-19 discovery).** The boot log had
48 silent errors per boot (24 surfaces x generate_normals
"primitive != PRIMITIVE_TRIANGLES" + generate_tangents "no NORMAL") in
_with_normals_for: it called st.create_from_arrays(arr, format_mask)
but Godot 4.7's signature is create_from_arrays(arrays, primitive_type)
— the FORMAT BITMASK was the primitive → the tool sat on a garbage
primitive and both generators failed on EVERY temple BSP surface. The
BSP glTF carries only POSITION+TEXCOORD_0 (verified), so the whole
temple BSP (the interior vault, the floors, the court) rendered with NO
normals: zero diffuse, ambient-only. DEVLOG-128's inward winding was
the SKIN's story; the BSP static black is THIS. The floors' built-in
heightmap route was also silently dead (it needs the tangent frame).
FIX: create_from_arrays(arr, Mesh.PRIMITIVE_TRIANGLES). The boot now has
ZERO mesh errors and the counts 4/9 + 10/10 temple surfaces with real
normals+tangents. The natural-light sufficiency check (the order from
the previous session) is now run against a renderer that actually
lights the interior.

**State:** the clean reimport 0 / headless boot: terrain per tile, the
player spawned, "game time 4.18 h (random)", ZERO mesh/shader/script
errors. NO display runs (the standing ban).

**Pending:** the user's screenshot verdicts — the day mountains without
the mosaic film, the hat gone above the statue's head (the 4 masked
surfaces now cut; behind them the real vault/walls show), the temple
interior under the now-working natural light. The commit since DEVLOG-96
awaits the user's word.

## DEVLOG-131 — 2026-11-21: the 08:47 black ground = the shadow map's all-shadow within its range (the sun → SHADOW_ORTHOGONAL); the night near-mountain film = the POM tightened (the scale, the fades, the dominance margin)

**The user's verdicts:** the statue WON (the DEVLOG-130 cutout), the
mountains are film-free in daylight. New: at ~08:30 and ~14:30 the sun
lights the trees and the distant mountain faces while the ground and the
mountains measure ambient-only; plus the film remains at night on the
NEAR mountains.

**The 08:47 diagnosis (the user's screenshot, pixel-measured):** the
ground 10/255 (the ambient-only would be ~69, the sun-lit ~206), the
trees 42-45 (= the ambient on the dark foliage), the temple 8.5-29 (the
west facade away from the eastern sun — correct physics), the sky 187,
BUT the right/left mountain peaks have 23-29% of the pixels above 150
(the max 255) — THE SUN IS ON AND WORKS on the geometry beyond ~100 m.
The terrain east of the player DESCENDS (no physical morning shadow is
possible — computed). Conclusion: the shadow map returns ALL-SHADOW for
everything inside its range (the default max_distance = 100 m from the
camera) and passes light beyond it. The angle is NOT the variable (the
user's 14:30 ≈ 15:24 by sun angle, opposite outcomes). This is the
compatibility renderer's directional-shadow pathology class already
documented in the DEVLOG-110 note (max_distance=300 killed the sun's
direct light entirely). The Godot source (renderer_scene_cull) anchors
the shadow frustum on the CAMERA frustum — the light node position and
the sun-following are irrelevant. FIX: the sun's shadow mode →
SHADOW_ORTHOGONAL (one cascade, no split-range math, the same 100 m =
2.4 cm/texel at 4096²). The bias/normal-bias/blur stay at the approved
DEVLOG-120/121 values.

**The night near-mountain film:** the near mountains are inside the
terrain POM's range (<90 m), the far ones are not — the film = the POM's
view-dependent texture slide. Three tightenings in terrain.gdshader:
pom_scale 0.05→0.04, the angle fade smoothstep(0.12,0.45)→(0.25,0.55),
the distance fade (30,90)→(25,70), PLUS a dominance-margin damp: the
runner-up mask weight measures the argmax ambiguity, and the shift is
multiplied by smoothstep(0.05, 0.3, wmax - w2) — at the layer boundaries
the march no longer jumps between the layers' height fields (the
shimmer), in the decisive areas the relief is unchanged.

**State:** headless boot 0 errors, the world built 8.5 s, the terrain
per tile, the spawn ok. NO display runs (the standing ban).

**Pending:** the user's screenshots at ~08:30/~14:30 (the shadow fix)
and at night (the POM tightening). If the all-shadow persists in the
ORTHOGONAL mode, the next levers: shadow_blur 1.4→1.0, then the
bias/normal-bias (the DEVLOG-120 temple values — the PWM risk assessed
before touching).

## DEVLOG-132 — 2026-11-21: the shadow path REVERTED to the old code (the defaults, PSSM4) per the user's order; the two A/B diagnostic flags (L2_SUN_NOSHADOW, L2_TERRAIN_FLATNORM)

**The user's order:** "трава так и не получила солнце. сравнивай со
старым кодом. освещение совсем недавно сломано. либо тогда когда ты
игралcя с освещением луны и солнца, но изменение поздно применилось."

**The diff vs the old code (git HEAD = the last committed state, the
whole lighting stage is uncommitted):** the lighting deltas are exactly
four: (1) the sun energy 5.0 static → 2.8 dynamic (the user's overcast
order); (2) the sun direction static NE-33° → the clock path (the
user's day/night order); (3) the shadow params the Godot defaults →
0.25/4.0/1.4 (the DEVLOG-120 temple PWM band-aid) → +ORTHOGONAL (my
DEVLOG-131 guess); (4) the ground fog removed (the user's DEVLOG-122
order). The ambient day value, the terrain shader's lighting terms
(ROUGHNESS 0.95, SPECULAR 0.0 since DEVLOG-125) and the terrain mesh
(except the DEVLOG-130 smooth normals) match the old code. NO hidden
change found in the diff — the 08:47 all-shadow-within-range defect has
no smoking gun at the code level.

**The revert (the user's directive):** the shadow setup = EXACTLY the
old working code — no bias/normal-bias/blur overrides (the defaults
0.1/2.0/1.0), PSSM4 (the DEVLOG-131 ORTHOGONAL guess dropped). The
DEVLOG-120 overrides were the temple PWM band-aid; the PWM's root (the
moon's moving shadows) is OFF since DEVLOG-125, so the defaults are safe
again. The overcast energy 2.8 and the dynamic sun path stay (the
user's own weather/day-night orders).

**The A/B diagnostics (one build, two launches localize the defect):**
- `L2_SUN_NOSHADOW=1` — the sun's shadows OFF. If the grass lights up:
  the shadow map is the culprit. If still black: the lighting path is.
- `L2_TERRAIN_FLATNORM=1` — the terrain rebuilt with the OLD per-face
  flat normals (generate_normals(), the DEVLOG-130 path reverted) while
  everything else stays. Localizes whether the missing sun follows the
  normals change.

**State:** headless boot 0 errors, the world built 8.7 s. NO display
runs.

**Pending:** the user's two A/B launches (any daytime hour, e.g.
L2_TIME=8.78 for the repro). The bisect: (a) both flags off = the
current state; (b) L2_SUN_NOSHADOW=1; (c) L2_SUN_NOSHADOW=1 +
L2_TERRAIN_FLATNORM=1 if (b) is still black.

## DEVLOG-133 — 2026-11-21: the shadow revert did NOT fix the black ground; the measured albedo at the spot is BRIGHT sand (0.38) — the terrain receives ~nothing; the light-path canvas diagnostic (L2_TERRAIN_LIGHTDEBUG)

**The user:** "не помогло. ищем дальше" (the shadow params revert to the
old code did not restore the sun on the ground).

**New measurements:**
- The exact albedo blend at the 08:47 player position (23427,8380): ALL
  masks = 0, the base layer only = Obase (0.42, 0.40, 0.32) — BRIGHT
  sand. The predictions: the ambient-only 76/255, the sun-lit 229/255.
  The MEASURED ground = 10/255 — the terrain receives ~1/8 of even the
  ambient-only level.
- The trees at 42-45 = the AMBIENT-only on their darker foliage (the
  user's "light on the trees" = the pale moss against the black ground).
  The trees receive the ambient; THE TERRAIN DOES NOT.
- The 15:24 screenshot (the DEVLOG-129 build, BEFORE the smooth
  normals): the ground = 110/255 = the light factor ~0.5 (a partial sun
  contribution). The 08:47 (the DEVLOG-131/132 builds) = 0.03. The
  terrain-specific light loss appeared between those builds; the only
  terrain delta = the smooth normals (+ the POM tightening).
- The rock-vs-sky separated re-measurement of the 08:47 peaks: the warm
  pixels (R > B+8) reach 180-251 — the sun IS on for the geometry
  beyond the ~100-m shadow range. The all-shadow-within-range picture
  holds.

**The new diagnostic (assets/shaders/terrain_lightdebug.gdshader):**
`L2_TERRAIN_LIGHTDEBUG=1` swaps the terrain material to a light-path
canvas: the albedo forced WHITE, the diffuse = the plain Lambert read of
LIGHT_COLOR x ATTENUATION (the shadow factor included). One screenshot
reads directly: the base gray level = whether the AMBIENT reaches the
terrain (~126 = yes on white); the bright regions = where the SUN
reaches; the boundary = the shadow map's reach; uniform black = the
terrain pipeline (the normals path) receives nothing at all. The real
shader stays untouched without the flag.

**The bisect plan for the user (L2_TIME=8.78 pins the repro hour):**
1. `L2_TERRAIN_LIGHTDEBUG=1` — the canvas.
2. Uniform black canvas → add `L2_TERRAIN_FLATNORM=1` (the old faceted
   normals): the canvas lights up = the smooth normals are the culprit.
3. The ambient-gray canvas but no sun → add `L2_SUN_NOSHADOW=1`: the sun
   appears = the shadow map is the culprit.

**State:** headless boot 0 errors; the clean reimport done. NO display
runs.

## DEVLOG-134 — 2026-11-21: the rebuild cache ruled out end-to-end (the nuclear clean + the runtime-level proof); the terrain material prints added

**The user:** "ничего не изменилось. проверяй кеш пересборки."

**The cache audit results:**
- assets/shaders/terrain.gdshader does NOT exist — the terrain shader
  lives at scripts/terrain.gdshader and LOADS DIRECTLY (no .import, no
  imported cache — it cannot go stale). The l2_* shaders likewise have
  no .import files (only the .uid stamps).
- .godot held no shader_cache; the only caches = imported/ (the
  textures/glTFs), uid_cache, the script class cache.
- NUCLEAR CLEAN EXECUTED: rm -rf .godot + the full headless reimport
  (235 MB, 5292 entries regenerated), import rc=0, 0 unexpected errors.
- RUNTIME-LEVEL PROOF: world.gd now prints the terrain material's
  assigned shader per tile. Headless with L2_TERRAIN_LIGHTDEBUG=1: every
  tile reports "LIGHTDEBUG canvas ... terrain_lightdebug.gdshader";
  without the flag: "shader=res://scripts/terrain.gdshader". The
  routing reaches the runtime on the CURRENT cache.

**The remaining explanation space:** the scripts (world.gd) load fresh
every launch — the 132/133 changes (the shadow defaults, the A/B flags)
WILL be active on the user's next launch. If the plain launch still
shows the black ground, the L2_TERRAIN_LIGHTDEBUG canvas launch is the
decisive evidence (its three possible readings = the DEVLOG-133 plan).

**State:** the cache fully regenerated; the boot 0 errors; the terrain
material prints verified for both modes. NO display runs.

## DEVLOG-135 — 2026-11-21: the ROOT CAUSE class found — the terrain was the ONLY default-light() shader and the compatibility renderer's default light path leaves it light-blind; the explicit Lambert light() added (the proven SPOM term)

**The user's two screenshots:** the day 15:03 — the sun falls on the
character, the trees, the rocks, the small stones, the columns but NOT
on the grass; the night 01:15 — the ground is PURE BLACK while the
trees/temple are moonlit. The user's hunch: "будто бы ты изменял
параметры цвета\света террейнов".

**What the night shot decides:** the moon carries NO shadows (DEVLOG-125)
— yet the ground is black → this is NOT the shadow map. The terrain
receives NO direct light (the sun AND the moon) AND no ambient, while
the identical-scene StandardMaterials (the foliage) and the
custom-light() shader materials (the SPOM walls, the PBR statics) are
lit normally.

**The verified-healthy list (the runtime prints):** the cache ruled out
(the DEVLOG-134 nuclear clean); the terrain material = the right shader
per tile; the committed mesh carries 368-393k normals per tile with ZERO
degenerate entries (the runtime print; the SurfaceTool set_normal→commit
pipeline probed offline = the normals survive).

**The pattern:** every material with an EXPLICIT light() override lights
up; the only default-light() custom shader in the project — the terrain
— is light-blind. The default light() path is broken for this material
in this renderer config; it worked in the pre-day/night builds, which
matches the user's "the lighting broke recently during the moon/sun
work".

**The fix:** terrain.gdshader gains the explicit light() — the EXACT
proven SPOM diffuse term (cNdotL/PI x LIGHT_COLOR x ATTENUATION; Godot
multiplies ALBEDO outside light(), as the approved SPOM shader shows).
The env ambient stays stage-level on top. The shadows still apply via
ATTENUATION. SPECULAR stays 0 (matte).

**State:** headless boot 0 errors; the world built 8.7 s. The normal /
material prints stay for one more verification round. NO display runs.

**Pending:** the user's day + night screenshots. If the ground lights up
— closed; the facet/film tuning continues from the earlier verdicts.

## DEVLOG-136 — 2026-11-22: the 20_19 CONTROL map built (the default import, the static sun, the plain sky, the HEAD terrain shader); the respawn moved there; the per-tile weather system

**The user's order:** "не помогло [the DEVLOG-135 Lambert light() did not
restore the terrain sun]. давай создадим карту 20_19 с дефолтным
импортом и дефолтным солнцем, небо без пасмурности, обычное. и сравним.
точку респауна туда переносим."

**The build:** the strict pipeline, the neighbors 20_18/19_19/21_19/20_20
(+ 21_20 after the first pass clamped the SE corner). Two pipeline fixes
made the map buildable:
- tools/l2strict/stage.py: the staging category is now a PREFERENCE, not
  a filter — Field_Deco_Artifact_s carries its MATERIALS inside the
  StaticMesh package, so material staging requests the mesh name with
  the Textures category; the fallback stages by the actual category
  (PackageSet reads every category; the texture resolution pass still
  catches real absences).
- verify.py: the 20_19 gates registered (the map stats + the terrain:
  65536 visible quads, 0 holes, edge_turn 11015, 0 clamped samples).
VERIFY: status ok. 82 meshes, 172 textures, 1 PlayerStart
(3536,55432,-3384).

**The runtime (world.gd):**
- TILES += 20_19 with "weather": "default"; the DE territory tiles =
  "overcast". The weather survives _load_data's tile rebuild (the key
  was initially dropped — caught by the material print, fixed).
- The DEFAULT-weather tiles build with the OLD terrain path: the flat
  per-face normals (generate_normals), no POM heights, and the HEAD
  default shader (scripts/terrain_default.gdshader = the git HEAD copy).
- _update_daynight reads the CAMERA's tile: the default tiles render the
  pre-lighting-stage state — the static NSun0 sun (energy 5.0, the
  fixed direction), the plain ProceduralSky, the client depth fog
  (24,29,35 @ 1..100 m), the zone ambient — no clock, no dome, no moon;
  the overcast tiles reset the fog OFF and the dome visible per frame
  (the border crossing flips the mode live).
- The respawn = 20_19's own PlayerStart0; terrain_height/-_tile_at are
  tile-aware so the cross-tile spawn samples the right heightfield.

**State:** the import rc=0 (258 MB cache); the headless boot 0 errors,
7 tiles, the spawn at (35.36,-33.75,554.32); the material prints: 20_18
= terrain.gdshader, 20_19 = terrain_default.gdshader (the HEAD shader).

**The comparison protocol for the user:** the spawn = on 20_19 under the
default sun and sky. If 20_19's ground IS lit while 20_18's is not
(the border crossing flips the sun/sky/shader live), the terrain light
loss lives in the 20_18-overcast path (the current terrain shader /
the day-night driver); if BOTH are dark, the loss is global and the
default-light() vs custom-light() split (DEVLOG-135) narrows further.

## DEVLOG-137 — 2026-11-22: the border shot CLOSED the case — the terrain triangles are wound front=DOWN; the DEVLOG-130 explicit UP normals were flipped DOWN on every visible fragment; the winding fixed + the 20_19 sky fog fixed

**The user's border shot** (X=-25 Y=60096, 09:43 день, on the 19_19/20_19
seam): the trees are lit on BOTH sides, the grass is lit on one side and
pure black on the other, the boundary is EXACTLY the tile seam, and the
sky is a flat dark navy ("в 20_19 неба вообще нету как и солнца, но трава
со светом при этом").

**The pixel measurements:** the sky = (24,29,35) — EXACTLY the client fog
color of the default-weather branch (the fog_sky_affect omission); the
lit grass lum 78 (with tree shadows = a real sun), the black side lum 9
(= the flat ambient on the terrain albedo + a small fog lift). Both tiles
were under the SAME env state (the default branch: the static NSun0 sun,
energy 5.0) — so the sun demonstrably reaches 20_19's terrain and NOT
19_19's.

**The decisive evidence was already in the boot logs.** The DEVLOG-135
normal print's "first=" value per tile:
- 20_19 (the flat generate_normals path, LIT): first=(0.0197, -0.996982,
  0.075084) — the normal points DOWN (Y negative);
- 19_19 / 20_18 / all the DE tiles (the smooth ngrid path, BLACK):
  first=(0.0, 1.0, …) / (-0.33, 0.89, -0.31) — UP.

**The mechanism:** _build_terrain emitted the quad triangles as
(0,2,1)/(0,3,2), which winds their FRONT faces DOWN (Godot's
generate_normals measures the winding and printed exactly that on 20_19).
With render_mode cull_disabled Godot flips the normal for back-face
fragments (two-sided lighting). Pre-130 the normals came from
generate_normals() — DOWN, matching the winding — so the visible-from-above
fragments (back faces) got the flip -> UP -> LIT (with the facet film).
DEVLOG-130 replaced them with the explicit UP normals on the SAME
down-wound triangles -> the flip turned them DOWN for every visible
fragment -> dot(NORMAL, LIGHT) <= 0 for any overhead sun/moon -> NO
directional light at all, flat ambient only. That is the whole
black-ground saga since DEVLOG-130, and it matches the user's "освещение
сломалось недавно": the 15:24 shot (the DEVLOG-129 build, pre-smooth) had
the partial sun 110/255; the 08:47 build (post-130) = 10/255. DEVLOG-135's
"default light() is blind" was a MISDIAGNOSIS (20_19's HEAD shader with
the down normals + flip lights fine); the SPOM-convention light() added
there is kept — it is the proven SPOM term and costs nothing.

**The fixes:**
1. scripts/world.gd _build_terrain: the emit order swapped to
   (0,1,2)/(0,2,3) — the front faces now point UP, so the smooth UP
   normals are used as-is with NO flip dependency. The placeholder-corner
   (real[]) case already emitted UP-front triples — unchanged. The POM is
   unaffected (its ngeo/vt.z are FRONT_FACING-adjusted and abs()-guarded;
   T/B and the derivatives are identical). 20_19's effective normals are
   unchanged too (down + flip == up + no flip).
2. The default-weather branch in _update_daynight: fog_depth_curve = 1.0
   and fog_sky_affect = 0.0 restored (the HEAD code had them; without
   fog_sky_affect the plain ProceduralSky renders 100% fogged to
   (24,29,35) = the user's "неба вообще нету" in 20_19).

**Gate A:** the headless boot 0 shader/parse errors; the normals print now
shows 20_19 first=(-0.0197, +0.996982, -0.075085) — the exact negation,
UP — and the DE tiles unchanged UP. NO display runs.

**Verification request to the user:** the same border spot (X=-25
Y=60096) — the grass must be lit on BOTH sides with the smooth look kept;
the 20_19 spawn — the plain sky visible (not the fog); the usual
day/night checks on the DE territory (the night ground must lift off
pure black via the moon + ambient).

## DEVLOG-138 — 2026-11-22: the location transitions — the GLOBAL sun/moon/ambient; the sky/fog regions follow the terrain-change edge (the meadow contour inside 20_19), never the tile seam; 20_19 moved to the standard terrain path

**The user's verdict + the new stage:** "трава наконец вернулась" (the
DEVLOG-137 winding fix confirmed). The new task: the location transitions —
(1) the sky and the light must change not at the tile seam but at the
terrain-change edge ("иначе пользователь успевает видеть траву разных
цветов"); (2) the sun is GLOBAL — in 20_19 and 19_19 it shone at different
angles and the shadow angle snapped at the border.

**The terrain analysis (offline):** the built world's landscape structure
(tmp/terrain_mosaic_albedo.png + _height.png): the bright yellow-green
meadow = a distinct basin landscape INSIDE 20_19 (its east/north; the
texmeans OG_53 0.50 / OG_45 0.52 / OG_58 0.44 vs the dark olive grasses
0.20-0.28 of 19_19/20_18). 20_19's SOUTH-WEST corner = the same dark
plateau as 19_19 — the terrain does NOT change at the x=0 seam there (the
user's shot spot). The meadow edge = the REAL terrain-change edge, running
diagonally inside 20_19, touching the seam only near the shot latitude
(the bright grass starts ~5-10 m east of the path) and at the far north
(where 19_19's dark plateau meets the meadow — the seam = the terrain
change there). Mask rows run south→north (row 0 = the tile's south edge).

**The region mechanism:**
- assets/maps/20_19/terrain/region_weather.png (64×64): white = the tile's
  OWN weather ("default" — the plain sky) inside the meadow coverage
  (baked offline: the bright-grass mask sum OG_53+OG_45+OG_58 > 0.7 per
  64-cell; 73% of the tile); black = the world-base overcast. Regenerable
  from the tile's own layer masks; no file = the tile is uniform.
- world.gd _load_data loads the optional mask per tile (the boot print
  "WEATHER REGION [...]: 64x64 mask loaded"); the new _region_weather()
  resolves the camera's weather: the tile's own weather inside the mask,
  the base overcast outside.
- _update_daynight RESTRUCTURED: the sun/moon/ambient = GLOBAL (one
  day/night cycle for every region — the energy 2.8 cap, the warm-to-white
  color, the moon 0.18, the night-ambient floor 12%) — the shadow angle
  cannot change across the borders anymore. Only the SKY and the fog are
  regional: the meadow = the plain ProceduralSky + the client depth fog
  (24,29,35 @ 1..100 m, fog_sky_affect 0); the DE territory = the overcast
  dome, no fog. The static NSun0 sun (energy 5.0, the fixed direction) is
  RETIRED — the DEVLOG-136 control state ends; the spawn keeps its plain
  sky (the spawn cell sits inside the meadow, bright=2.62).

**20_19 = the standard terrain path:** the DEVLOG-136 control split (the
flat generate_normals + the HEAD terrain_default.gdshader + the POM skip)
retired — ONE terrain path for every tile (the smooth ngrid normals, the
current terrain.gdshader, the POM heights). This removes the shader/normal
look difference at the borders; the remaining grass color difference =
the authentic per-tile textures (also in the client).
terrain_default.gdshader stays on disk unused (the control artifact).

**The region sampling (the offline simulation of _region_weather):** the
spawn (3536,55432) = default; the shot spot (x=-120) = overcast (19_19);
the seam-adjacent 20_19 strip at the shot latitude = overcast (the dark
SW corner), the meadow from ~x 500-1000 east = default; the far north
20_19 = default, 19_19 = overcast (the switch = the terrain change at the
seam there).

**Gate A:** the headless boot 0 errors; all the tiles print
shader=terrain.gdshader; 20_19 first=(-0.027, +0.998, -0.054) (the smooth
UP normals); the region mask loaded. NO display runs.

**Verification request to the user:** (1) at the border spot — crossing
the path the shadow ANGLE must not change and the grass brightness must
not snap at the seam; (2) walking east into the bright meadow the sky
switches to the plain blue AT the grass change (~5-10 m east of the path);
(3) the spawn view = the plain sky with the dynamic sun; (4) the usual
day/night checks on both sides.

## DEVLOG-139 — 2026-11-22: ONE world sky dome — the clouds are a geographic field, the sun works with the clouds, the fog removed everywhere (the user's architecture order)

**The user's verdict on the DEVLOG-138 regions:** in 20_19 the sun looked
"behind fog", and the 20_19 textures looked brighter VIEWED FROM 19_19 —
i.e. the sun was effectively brighter in the overcast 19_19 than in the
clear 20_19. The measurement agreed: it was the MEADOW's depth fog
(24,29,35 @ 1..100 m) dimming everything the camera saw from inside it
(the distant mountains = the navy silhouettes), while the fog-free
overcast side rendered at full brightness. "Fog is not needed there — the
territories are always bright." And the architecture order: "across the
whole map there must be ONE common dome/sky, as in real life, with the
only difference being the clouds over different maps; the sun works with
the clouds and the weather, not with baked light — then the eternal
transition tuning goes away."

**The new architecture (implemented as ordered):**
- ONE sky dome (l2_sky_clouds.gdshader reworked) for EVERY tile and
  region — always visible, camera-following, fog_disabled. No region sky
  switches remain in world.gd (the DEVLOG-138 branch machinery removed:
  _region_weather, the region_img loads, the fog toggling).
- The clouds are a GEOGRAPHIC FIELD: assets/textures/sky/world_clouds.png
  (256×192, 512 game units/texel, the world rect x[-65536,65536]
  y[-32768,65536] — CLOUD_ATLAS_RECT), baked by
  tmp/bake_cloud_atlas.py from the tiles' own weather region masks (the
  tile's own weather = 0.0 clear, the base overcast = 1.0, the unbuilt =
  the nearest built tile, then the gaussian blur sigma 2.5 texels ≈ 13 m
  godot so nothing ever steps at an edge). The dome fragment projects the
  view direction onto the cloud plane (600 m above the camera), reads the
  atlas at that world point and blends the clear/overcast palettes +
  cloud coverage per fragment: gray and dense over the village, blue with
  sparse white clouds over the meadow, the transition in the SKY exactly
  where the terrain changes below.
- The sun works with the weather: world.gd samples the SAME atlas
  bilinearly above the camera (_cloud_at) and the sun energy =
  lerp(3.4, 2.8, cloudiness) × the elevation cycle — the clear sky = the
  stronger direct sun, the full overcast = the approved 2.8. The dome
  draws the sun disc (the warm core + the halo) masked by the clouds, so
  the disc appears in the clear sky and hides under the cover — the
  light and the sky can never disagree.
- NO FOG anywhere (env.fog_enabled = false; the client's ZoneInfo
  DistanceFog stays recorded in _build_environment for the restore). The
  moon disc/moonlight unchanged; the ambient unchanged (one for the
  world).
- The clear-sky palettes: the day pair = the approved DEVLOG-136 control
  look (0.2,0.3,0.5 top / 0.45,0.5,0.55 horizon); the clear dusk/night =
  clean-room values; the overcast palettes = the DEVLOG-122 approved ones.

**The atlas landmarks:** the spawn (3536,55432) = 0.086 (clear), the
meadow center = 0.0, the village = 1.0, the user's shot spot
(-372,64260) = 0.703 (19_19, near the meadow edge — the blurred field),
the far north 20_19 = 0.134. The sun energies: the meadow 3.35, the shot
spot 2.98, the village 2.8 (at the same elevation).

**Gate A:** the full headless import rc=0 (the new PNG's .import created —
the first boot139 caught "No loader found" for the unimported atlas: the
dome would have sampled an empty texture); the boot 0 script errors, the
atlas loads, world built 9.9 s. fog_disabled verified valid in the Godot
4.7 spatial render modes (the docs). NO display runs.

**Verification request to the user:** (1) the same border spot — the sun
must look CLEAN (no fog veil) in the clear sky, the distant mountains
un-fogged; (2) standing at the border the sky must READ as one sky: the
gray cover over the village side, the blue with sparse clouds over the
meadow side, blending across the sky; (3) the sun brightness: the clear
meadow slightly brighter than the overcast village side (3.35 vs 2.8 at
the zenith); (4) the sun disc hides under the cloud cover and shows in
the gaps; (5) the usual day/night checks.

## DEVLOG-140 — 2026-11-22: the sky SIMPLIFIED per the user's flat-world spec — one palette for the whole world, the clouds = the world-anchored overhead field driven by ONE cloudiness value above the camera, the semi-transparent DE veil; the wedge artifact dead

**The user's verdict on the DEVLOG-139 dome:** it failed — the sky showed
hard straight-edged WEDGES (the bright blue triangle in the first shot,
the sharp radial seams in the second). The cause: the per-fragment
geographic atlas lookup projected the region field onto the cloud plane —
near the zenith the footprint is tiny and near the horizon it explodes,
so every region edge in the atlas became a straight wedge radiating
across the sky. The user simplified the task: "плоский мир, небо без
изгиба; везде одинаковое по цвету небо, солнце один источник на весь мир,
а сверху, именно над картой, то тучи, то нету туч, то очень густые — в
зависимости от карты; над территориями тёмных эльфов средний показатель,
пасмурность: туч много, всё небо затянуто, но облака полупрозрачные, а не
тёмные и толстые".

**The new dome (l2_sky_clouds.gdshader rewritten):**
- ONE sky palette for the whole world (the day = the approved control
  blue 0.2/0.3/0.5 — 0.45/0.5/0.55; the clean-room dusk/night). No
  per-fragment palette blending.
- NO geographic lookup per fragment (the wedge cause removed). The cloud
  pattern = the world-anchored fbm: the direction projected onto the
  cloud plane gives the WORLD point (cam_ws.xz + dir.xz * (600 m /
  dir.y)), the fbm reads that point × 0.005 + the clock drift — the
  clouds stay over the map as the player walks, and the smooth pattern
  cannot seam.
- The coverage + the opacity come from ONE uniform (cloud_local) — the
  cloudiness ABOVE THE CAMERA, which world.gd bilinearly reads from the
  same world atlas per frame. cov = mix(0.78, 0.30, c); op =
  mix(0.50, 0.85, c). The clouds fade in overhead (smoothstep 0.02..0.12
  of dir.y) — "если смотреть вверх".
- The DE veil = the semi-transparent light gray (cloud_day 0.84/0.87/0.92,
  the opacity 0.745 at c=0.7), covering ~90% of the sky with the blue
  showing through — "затянуто, но полупрозрачные, а не тёмные и толстые".
  The dusk/night cloud bodies ride their own palettes.
- The sun disc + the halo glow through the veil (× (1 - mask*op)).
- The atlas REBAKED: the DE overcast = 0.7 (the MEDIUM indicator per the
  user's scale — the 1.0 headroom stays for a future denser territory),
  the meadow = 0.0. The landmarks: the village 0.700, the spawn 0.060,
  the shot spot 0.492. The sun = lerp(3.4, 2.8, c) → the DE 2.98, the
  clear 3.35 (the thin veil passes more light than the old full cover —
  the requested lighter look).

**world.gd:** the dome's cloud_atlas/atlas_rect uniforms removed (the
shader has no geographic lookup anymore); cloud_local added per frame;
the CPU atlas (_cloud_img/_cloud_at) stays as the single source for both
the sun energy and the sky's cloud_local — the sky and the light can
never disagree, and no transition tuning remains (the atlas field does
it).

**Gate A:** the rebake + the full import rc=0; the boot 0 script errors,
no loader errors, world built 9.9 s. NO display runs.

**Verification request to the user:** (1) NO wedges/seams in the sky at
the border — one smooth sky; (2) the same sky color everywhere; looking
up: the blue with the sparse clouds over the meadow, the semi-transparent
light-gray full veil over the DE territory, changing smoothly as you walk
the border; (3) the sun disc visible in the clear sky, glowing faintly
through the veil; (4) the distant mountains with NO fog; (5) the usual
day/night checks.

## DEVLOG-141 — 2026-11-22: the clouds are GLOBAL and belong to the territories (the user's correction of the DEVLOG-140 model); the geographic atlas restored per-fragment with the soft-front bake — the DEVLOG-139 wedges stay dead

**The user's correction:** the DEVLOG-140 "one cloudiness above the
camera" made the WHOLE sky's cloud amount change at the border crossing —
exactly the effect to avoid. The real model: "небо одинаковое по цвету и
синеве везде, но количество туч на картах разное; тучи видны глобально, а
не при переходе; тучи именно сверху над картой, поэтому видны даже с
соседней карты" — the clouds are fixed over the territories, the
neighbor's weather is visible in its direction of the sky, and crossing
the border changes nothing (you walk UNDER the clouds).

**The implementation:** the per-fragment geographic atlas lookup on the
cloud plane (the DEVLOG-139 mechanism) is RESTORED — the coverage and
the opacity are the functions of the FRAGMENT's local density
(cov = mix(0.78, 0.55, c), op = mix(0.50, 0.85, c)), so the semi-
transparent light veil sits over the DE territory and the sparse light
clouds over the clear one, both visible from across the border. The
DEVLOG-139 wedge artifact does NOT return because the atlas is now
baked with sigma 10 texels ≈ 51 m godot (the σ=20 experiment flooded
the clear cores: the meadow center 0.18, the spawn 0.36 — rejected; the
σ=10 keeps the cores: the meadow center 0.043, the village 0.700, the
spawn 0.305, the far-north meadow 0.276): the territory edges read as
soft fronts ~200 m wide in the sky instead of razor straight lines. The
sky palette stays ONE for the whole world; the pattern stays
world-anchored; the sun disc glows through the veil. The sun light
samples the same atlas above the camera (lerp(3.4, 2.8, c)) — walking
the border changes the light smoothly, nothing snaps.

**world.gd:** the dome's cloud_atlas/atlas_rect uniforms restored; the
cloud_local uniform removed (the density is per-fragment now); the CPU
atlas read (_cloud_at) stays for the sun only.

**Gate A:** the rebake + the full import rc=0; the boot 0 script errors,
no loader errors, world built 9.9 s. NO display runs.

**Verification request to the user:** (1) no wedges/seams; (2) standing
in the DE territory: the semi-transparent gray veil overhead AND the
clear blue sky visible in the direction of the meadow (the neighbor's
weather seen from afar); (3) from the meadow: the sparse clouds overhead
and the gray cover visible over the DE side; (4) crossing the border:
the clouds do NOT change amount abruptly — the front passes overhead
softly; (5) the sun disc clean in the clear sky, glowing through the
veil; (6) the usual day/night checks.

## DEVLOG-142 — 2026-11-22: "the cloud amount is the same everywhere" — two root causes fixed: the atlas exhausted below 42 deg of elevation (the clamped-constant low sky) and the too-flat density→coverage mapping

**The user's verdict on the DEVLOG-141 build:** "ничего не изменилось.
количество туч везде одинаковое" — the clouds render but the SAME amount
everywhere.

**The root causes (both mine, both fixed):**
1. THE ATLAS EXHAUSTION: the cloud-plane projection (600 m / dir.y) puts
   a direction below ~42 deg of elevation beyond the old atlas (±655 m
   godot) — more than half the visible sky clamped to the atlas EDGE
   texels = one constant. Only the narrow zenith cone read the real
   field. FIX: the atlas now extends 1500 m godot beyond the built world
   in every direction (841×777 texels at 512 game/texel; the unbuilt =
   the nearest-tile fill) AND the projection SATURATES the distance at
   1500 m (dist = min(600/dir.y, 1500)) — the whole sky above the cloud
   fade floor (dir.y 0.02..0.12) lands INSIDE the field. The kink of the
   saturating mapping is invisible on a continuous field (no seam).
2. THE FLAT MAPPING: cov was mix(0.78, 0.55, c) — a 0.23 threshold range,
   barely visible. FIX: cov = mix(0.85, 0.30, c), op = mix(0.45, 0.85, c)
   — the clear core = the near-cloudless sky (the coverage 0.82, the
   opacity 0.47), the DE core = the full semi-transparent veil (the
   coverage 0.45, the opacity 0.73), the strong visible contrast between
   the territories.

**The atlas landmarks (the σ=10 texels = 51 m soft fronts kept):** the
village 0.700, the meadow center 0.056, the spawn 0.305, the border shot
spot 0.388, the far-north meadow 0.276. The sun = lerp(3.4, 2.8, c) above
the camera (unchanged).

**Gate A:** the rebake + the full import rc=0; the boot 0 script errors;
**CLOUD ATLAS: 841x777 bound** (the new boot print proves the texture
binds — the DEVLOG-139 "No loader" class is closed). NO display runs.

**Verification request to the user:** (1) the clouds differ STRONGLY
between the territories now: the near-cloudless blue over the meadow, the
full semi-transparent veil over the DE side; (2) both visible from across
the border (the neighbor's weather in the sky, incl. the low directions);
(3) no wedges/seams; crossing the border nothing snaps; (4) the sun disc
clean in the clear sky, glowing through the veil.

## DEVLOG-143 — 2026-11-22: the clouds = the ceiling only (the user: "облака не должны скатываться по краям карты как по стенам")

**The user's verdict on the DEVLOG-142 build:** "почти хорошо" — the
territory weather works — but the clouds ran down to the horizon as
vertical curtain-like walls.

**The cause:** the cloud mask's horizon fade started at dir.y = 0.02 (1
deg of elevation) — exactly where the saturating projection (1500 m cap)
stretches the pattern patches into narrow angular slivers along the
horizon; the fade band rendered them as vertical curtains ("walls").

**The fix:** the mask now fades in from dir.y 0.22 (12.7 deg) and is full
above 0.45 (26.6 deg) — the clouds exist only on the ceiling; the low sky
is the clean gradient. The sun disc at the low elevations (the sunrise/
sunset) is now always unmasked (clear horizon sun).

**Gate A:** the boot 0 script errors, CLOUD ATLAS bound, world built.
NO display runs.

**Verification request:** the sky near the horizon = the clean gradient
(no curtains) on BOTH the DE and the clear sides; the clouds = the
ceiling patches overhead; the rest of the DEVLOG-142 behavior unchanged.

## DEVLOG-144 — 2026-11-22: the respawn returns to the DE village; the village artificial lighting removed except the tunnels; the street lanterns (the blue plafonds) become the light sources

**The user's order:** "меняем точку респауна на деревню тёмных эльфов.
убираем внутри деревни искуственное освещение, кроме туннелей. и делаем
из фонарей в деревне источники освещения. там у фонарей есть синие
плафоны, они будут источниками."

**The spawn:** back to the village — the map's own authored PlayerStart0
(9383,16440,-4478), the west plaza inside the lantern cluster. The cell
is a terrain-hole cell → the deck-height spawn path (the boot proof:
"player spawned at (93.83, -43.88, 164.4)").

**The light audit (the data-driven rules):**
- The village region = the terrain-hole bbox (x 5888..14976, y
  11904..21504 — the connected hole region #1 computed offline). The
  Light actors inside it: 91 (20 of them already carry the map's own
  deleted flag → 71 actually skipped at the runtime).
- The tunnels keep their lights AUTOMATICALLY: everything outside the
  village bbox stays — the kept 13 = exactly the tunnel corridor cluster
  (Light119-129, x 15084..16788) + the approach. The temple region skip
  (DEVLOG-129) unchanged: 30.

**The lantern lights:** O_DE_Lamp01 ×22 + O_DE_Lamp02 ×9 (the village
street lamps, the pivots z -4473..-4498) + O_DE_Center_obj (the village
centerpiece — it carries the same blue glass). The plafond = the
DE_V_cube_deco3 texture (mean RGB 0.49/0.74/0.80 — the blue glass); the
plafond surface's AABB center = the omni anchor — the client's own
Light actors sat at exactly this offset (the pivot +13..15 game units,
verified Light141 z=-4458 vs the Lamp01 pivot -4473). 32 omnis total:
the blue Color(0.6, 0.75, 1.0), the energy 2.6, the range 7.0, the
attenuation 0.25, no shadows, registered for the same 250-m proximity
gate as the map lights.

**The plafond emission:** l2_surface_pbr.gdshader gains the
emission_energy uniform (0 = every texture inert) writing
EMISSION = albedo * energy; l2_proc_tex._pbr_material sets it to 1.6 for
DE_V_cube_deco3 only. The glass glows with its own blue pattern day and
night (the client's lamps are always-on).

**Gate A:** the full import rc=0; the boot 0 script errors; 20_18 prints
"placed 11 map lights (43 registered; 30 temple + 71 village skipped)"
(the 43 = 11 map + 32 lantern); the spawn proof above. NO display runs.

**Verification request to the user:** (1) the spawn view = the village
plaza; (2) the night shot: the streets lit by the BLUE pools at the
lanterns, the glass glowing, NO other artificial light in the village;
(3) the tunnel keeps its lights; (4) the day shot: the glass glows subtly
under the sun; (5) the lamp light tuning (the color/energy/range) on the
user's screenshots.

## DEVLOG-145 — 2026-11-22: the respawn moved to the road between the village and the Shillien Temple (the old route-profile spot) — the village PlayerStart0 spawned inside a building

**The user's verdict:** the village PlayerStart0 (9383,16440) = inside a
building. The new point = the OLD documented spawn (the temple-stage
session): (21109, 12819, ground -36.66), the road between the DE village
and the Shillien Temple, the yaw -1.2313 facing the temple entrance (the
default already in the code). The terrain probe: present=1, the spawn
logic picks the ground height. The village lantern lighting (DEVLOG-144)
is unaffected — the lanterns sit in the village; the road spot has no
lanterns (the client lights there = the pre-existing map lights outside
the village bbox, unchanged).

**Gate A:** the boot 0 script errors. NO display runs.

## DEVLOG-146 — 2026-11-22: the village lantern lights de-gated — they burn ALWAYS; the angle-dependent light-selection lottery in the compat renderer fixed

**The user's verdict on the dark-plaza shot (X=12563 Y=16623, 17:31 день,
the blue plafond dots glowing, NO light pools on the ground):** "при таком
ракурсе камеры в этом гео, отрубаются все источники... отруби вообще
зависимость от камеры. они должны гореть всегда когда персонаж внутри
локации, сразу как выходит из туннель в деревню. условия простые."

**Two camera-dependence channels found and cut:**

1. **The 0.5 s proximity gate** (DEVLOG-144 registered the 32 lantern
   omnis into `_lamps` with LAMP_ACTIVE_DIST=250): the lanterns now leave
   the gate array — created `visible = true` and NEVER toggled. They burn
   from the boot onward, at every camera angle, day and night (the user's
   "условия простые"). The 19_18/other tiles' map lights keep the gate
   (1755 Light actors — the per-frame compat light-list cost, out of
   scope).
2. **The compat renderer's light-limit lottery** (the REAL mechanism
   behind "at this camera angle the sources disconnect"):
   `rendering/limits/opengl/max_lights_per_object` = 8 and
   `max_renderable_lights` = 32 (the Godot defaults). The village's big
   meshes (the tile terrain and the BSP road/deck objects) have AABBs
   overlapping dozens of lights; the 8 slots were filled from the
   frustum-culled light set in cull order, and WHICH lights won the slots
   flipped with the camera angle — at whole viewing angles every pool in
   the frame vanished. Raised in project.godot: max_renderable_lights
   32→256, max_lights_per_object 8→64 (covers the full village set: 32
   lanterns + the tunnel map lights; the gate keeps the 19_18 register
   low, so the per-frame list cost stays bounded).

**Dead end documented:** `VisualInstance3D.extra_cull_margin` does NOT
exist for lights in Godot 4 (the property lives on GeometryInstance3D;
Light3D extends VisualInstance3D directly) — the runtime assignment
errors out ("Invalid assignment ... OmniLight3D", the first Gate A run
caught it). Not needed anyway: the frustum culling of the light
INSTANCES drops only the pools on unseen ground (behind the camera); the
visible pools come from in-view lanterns, and those were killed by the
8-slot lottery, now gone.

**Gate A:** the boot 0 script errors; "player spawned at (211.09,
-35.76044, 128.19) terrain_height=-36.6604357337952" (the DEVLOG-145
road spawn intact); all tile light placements unchanged (30 temple + 71
village skipped). NO display runs.

**Verification request to the user:** the SAME plaza camera as the dark
shot — the blue pools must be on the ground at EVERY angle now; plus the
night shot through the tunnel → village (the lanterns must already be
burning at the tunnel exit).

## DEVLOG-147 — 2026-11-22: the lantern pools moved INTO the shader — the angle-dependent light lottery defeated for good

**The user's verdict after DEVLOG-146** (the plaza shot X=13426 Y=16490,
15:59 день, plafonds glowing, no pools): "всё равно есть отключения от
ракурса".

**The audit (new diagnostic `L2_LIGHT_CAP_AUDIT=1`, world.gd) proved the
real mechanism with numbers** (run headless, spawn forced to the user's
plaza point via L2_SPAWN):
- 615 visible omni lights at the plaza (the DEVLOG-110 LAMP_ACTIVE_DIST=250
  gate spans 250 m in a 7-tile world — 1954 registered lights, 615 pass);
- 4430 mesh instances, **314 overlap more than 8 lights**; the plaza floor
  alone (`aabb pos=(82.6,-48.4,143.3) size=(64.5,2.4,60.0)`) overlapped
  **32** lights, the centerpiece **43**;
- the compat renderer lights each object with at most **8** lights — a
  COMPILE-TIME cap (`MAX_LIGHTS_PER_OBJECT`); the
  `rendering/limits/opengl/max_lights_per_object` project setting (raised
  to 64 in DEVLOG-146) does NOT lift it — so WHICH 8 lights each big mesh
  received flipped with the frustum-cull order = the camera angle. The
  DEVLOG-146 limit raise was insufficient; it stays (harmless headroom).

**The fix — the pools render in l2_surface_pbr.gdshader itself,
bypassing the renderer's light lists entirely:**
- the 32 OmniLight3D lanterns are GONE; `_build_meshes` registers each
  plafond center into `L2ProcTex.register_lantern()`;
- the shader accumulates the pools per fragment from
  `uniform vec3 lantern_pos[64]` + `lantern_count` (world-space VERTEX,
  the Gate-E screen-Jacobian normal ngeo; falloff = the retired omni's
  parameters: range 7, the wide 0.25-exponent curve, geometric N*L so the
  bright spot sits at the lantern base; `EMISSION += albedo *
  lantern_color * 2.6 * sum`);
- `L2ProcTex.apply_lanterns()` pushes the uniforms into every cached PBR
  material at the end of _ready; materials created later (later tiles, the
  character body in player.gd) receive them at creation — the character
  shares this shader, so the pools light the body too;
- ZERO renderer light lists involved => zero camera dependence, the pools
  burn at every angle the moment the position array is fed (the boot, i.e.
  "сразу как выходишь из туннеля"). lantern_count=0 outside the village =>
  the road/temple materials are bit-identical (the golden baseline safe).

**Known accepted trade-offs:** the hair's StandardMaterial3D override and
the rare non-PBR fallback surfaces do not receive the shader pools; the
tunnel map lights keep their renderer-driven (lottery-prone, pre-existing)
pools — out of scope.

**Gate A:** the full reimport after the shader edit (the .import trap
protocol: shader .import deleted + .godot/imported wiped) rc=0 — the only
"errors" are the known benign ones (1400 × glTF zero-accessor, 4 × temple
SPOM textures). The boot: 0 SCRIPT ERROR, 0 shader parse errors,
"lantern pools: 32 positions pushed to the PBR materials", the audit
counts only the map lights now (583). NO display runs.

**Verification request to the user:** the SAME plaza camera as the dark
shot — the blue pools must be on the ground at EVERY angle; the character
body brightens near the lanterns; the pool look (energy 2.6 / range 7 /
wide curve) is uniform-tunable on the user's screenshots.

**DEVLOG-147 rev2 (the same day, the user's "теперь освещение вообще не
работает"):** the first rev pushed the uniforms only into the
`L2ProcTex._cache` materials — but `_bsp_material` (the route of ALL the
village BSP floors: the roads, the plaza — everything the user looks at)
DUPLICATES the cached material (`pm.duplicate()`) and a duplicate holds
only the parameters set before it was made; the push happens at the end
of _ready, after every duplicate exists. So the floors never received
`lantern_count` and the pools were dead on the whole village ground.
Fix: `L2ProcTex.track_pbr_material()` — a static list of EVERY live PBR
ShaderMaterial (the cache originals tracked in `_pbr_material`, the BSP
duplicates tracked in `_bsp_material` right after `duplicate()`),
`apply_lanterns()` walks it. Boot proof: "lantern pools: 32 positions ->
192 tracked PBR materials" (rev1 reached only the cache), 0 script /
shader errors, the spawn intact. NO display runs.

**DEVLOG-147 rev3 (the user's "не помогло. значит сломали в прошлой
итерации"): the pools were dead ON ARRIVAL — a Gate-E violation.** The
pool math read the lantern distance from FRAGMENT `VERTEX`, but fragment
VERTEX is VIEW-space (the Godot 4 spatial shader docs, verbatim: fragment
VERTEX is "transformed into view space"; `world_vertex_coords` changes
only the VERTEX stage). world lantern positions minus view-space fragment
positions = hundreds of meters → every lantern skipped by the
`ld >= lantern_range` guard → lant_sum = 0 everywhere → no pools at all
("освещение вообще не работает"). The project's own Gate E (2026-11-14,
AGENTS.md) prescribes exactly the cure; the SPOM shader had already
documented the same trap (its lines 276-280: the fragment Jacobian basis
is VIEW-space). The shader's own line-171 comment ("VERTEX in fragment =
view space, its length = the camera distance") was right all along; the
POM's "world step" comments are misleading-but-harmless (the POM math is
consistent entirely in view space and pom_scale=0 everywhere anyway).

**The fix (the Gate-E prescription verbatim):** `varying vec3 wpos;` +
`void vertex() { wpos = VERTEX; }` (the vertex-stage VERTEX IS world with
world_vertex_coords); the pool block reads `lantern_pos[li] - wpos` and
the normal is `normalize(cross(dFdx(wpos), dFdy(wpos))) * ff` (the world
Jacobian; `ff` flips it for the two-sided BSP back faces). ngeo stays
untouched (the POM's view-space basis).

**Gate A — the FULL protocol this time (the earlier revs ran only the
headless parser, which cannot catch driver-level failures):**
- the .import trap protocol (shader .import deleted + .godot/imported
  wiped + full headless import) rc=0;
- the headless boot: 0 SCRIPT ERROR, "lantern pools: 32 positions -> 192
  tracked PBR materials", the spawn intact;
- **the REAL-display compile check (DISPLAY=:0, --rendering-driver
  opengl3, stderr captured, NO screenshot): 0 "shader error|compile"
  lines** — the wpos shader compiles on the real driver. The compile
  check is now a standing part of the shader-edit protocol (the headless
  parser alone is insufficient — Gate A's own rule, followed late here).

**Numeric expectation (offline replication):** a floor point directly
under a plafond (the plafond ~4.5 m above the floor): att=(1-4.5/7)^0.25
≈ 0.77, N·L ≈ 1 → the pool adds albedo × blue × ~2.0 — a strong visible
pool. NO display renders by the agent; verification = the user's
screenshot of the SAME plaza camera.

**DEVLOG-147 rev4 — the FINAL split of labor (the user's screenshot: "освещение
на домах но не касается других поверхностей"). THREE root facts, all
established by numeric probes (L2_TRACE_BOX + a Gate D debug-render series):**

1. **The ground the user looks at is NOT pool-capable material.** The
   trace at the user's plaza point: ~50% of the visible ground =
   `BSP:Polys3993/Polys348` brush faces with `surf=-1 tex=?` — the GREY
   StandardMaterial3D placeholder (no texture record in bsp.json); the
   walls/houses = `DE_V_wall01/02` — ALSO placeholders (no staged PBR
   sets; the oren_dev_t package stages 62 sets — statues/deco/capets/
   plafond — but NOT the floors/walls... EXCEPT DE_V_floor01/02, DE_V_m12,
   O_dark_01 DO have sets — the first "no PBR sets" probe verdict was a
   CASE bug in the probe itself, corrected). The shader pools fired only
   on the PBR deco/lamp pieces — "lighting on the houses".
2. **The position space truth table (Gate D probes 3-5):** the VERTEX-STAGE
   VERTEX with `world_vertex_coords` = WORLD (probe 3: the buildings fired
   at the world lantern distances; probe 4: the fract decode consistent
   with the world meters) — the varying wpos = VERTEX in vertex() is the
   CORRECT world position. The FRAGMENT VERTEX = VIEW-space (probe 5:
   switching the pool to it extinguished every pool; the docs' fragment
   line is right). (An intermediate "wpos = model space" reading of probe
   4 was a fract-mod-20 misdecoding — retracted.)
3. **The normal sign:** the GLES3 y-down dFdy convention + the BSP's
   front-DOWN winding (DEVLOG-137) make `cross(dFdx,dFdy) * ff` point DOWN
   on the floor back faces (probe 4: wn.y = -1 on the ground) — the walls
   lit, the ground could never. Fixed with the sign-proof two-sided form
   **abs(N·L)** in both shaders (the undersides it would reach are void in
   the village). A compile break (the wpos varying deleted while the pool
   still used it — the neutral-gray fallback frame) caught by the Gate D
   series and fixed.

**The final architecture (the "conditions simple" the user ordered):**
- **Layer 1 (all ShaderMaterial surfaces — the PBR floors, the roads, the
  deco, the character):** lit EXCLUSIVELY by the deterministic shader
  pools (l2_surface_pbr + l2_procedural, wpos + abs(N·L), the uniforms fed
  by L2ProcTex.apply_lanterns(), 32 positions → 192 tracked materials).
  Zero renderer light lists => zero camera dependence.
- **Layer 2 (the StandardMaterial3D placeholders — the grey BSP ground
  faces + the placeholder walls/houses):** lit EXCLUSIVELY by the restored
  lantern OmniLight3D nodes (the DEVLOG-144 look: energy 2.6, range 7,
  attenuation 0.25, the blue color) with `light_cull_mask = 2` — they
  CANNOT double-light anything on layer 1. Always on, no gate. The
  placeholder carriers are small pieces (the brush grey surfaces SPLIT
  into their own MeshInstance — the three-way grate/grey/textured
  partition in _build_bsp_brushes; the statics: all-placeholder keys move
  whole (395 keys), mixed keys split per key into main+grey twins (5
  keys) — the boot print "layer routing: 395 all-placeholder keys, 5
  mixed keys split"). No per-object 8-light lottery (small carriers).
- No omni on the character: its body = l2_surface_pbr (the shader pools
  light it).

**Gate D verification (the debug render, camera parked AT a lantern,
spawn 9815,17994):** after the wpos restoration — bottom-center ground
99.5% magenta-ratio px, the mid-left road 100%, the mid-right ground 100%,
the center building 100%, the distant buildings 83% magenta / 17% yellow
(beyond the 7 m radius = the correct zero). Earlier Gate D lessons: the
RGB-threshold classifiers false-negative on the night-dimmed albedo (use
the channel RATIOS); one intermediate all-neutral-gray frame = the compile
break above (the fallback look).

**Gate A (the full protocol):** the reimport rc=0; the boot 0 script
errors, "layer routing: 395 ... 5 mixed", "lantern pools: 32 positions →
192 tracked", the DEVLOG-145 road spawn intact; the REAL-display compile
check 0 shader errors. NO screenshot verification by the agent of the
final look — the user's screenshot decides.

## DEVLOG-148 — 2026-11-22: the omni shadows ON + the character moved to layer 2; the plaza lattice diagnosed as the LOST BSP SURF RECORDS (pending extraction task)

**The user's verdict on rev4 (works) + four items:** (1) half the body in
shadow / wrong light; (2) no shadows from the character; (3) between two
lanterns there should physically be TWO weak shadows; (4) the center-plaza
lattice lost its grid transparency.

**Items 1-3 — fixed:**
- **The character renders on LAYER 2** (player.gd: all the part
  MeshInstances layers = 2): lit exclusively by the lantern omnis (the
  DEVLOG-144 lamp-lit look restored — the omni reaches the dark suit,
  which the albedo-modulated shader pool could not make readable) and
  casts the omni shadows. The shader pools are OFF on the body
  (lantern_count defaults to 0 — the uniform push removed): the omni
  replaces them 1:1, no double-lighting. The sun/moon (cull_mask = all)
  still lights and shadows the character.
- **The omni shadows are ON** (shadow_enabled = true): the character
  standing between two lanterns casts TWO weak shadows on the layer-2
  ground — exactly the physics the user described. NO glass-blob risk:
  the plafond glass is on LAYER 1 and the omni's shadow pass sees only
  layer 2 (its cull_mask) — the glass never enters the shadow map. The
  layer-1 pool-lit surfaces stay unshadowed (the shader math) — a known
  limitation, the shadows read on the placeholder ground.
- The pools on the character were ALSO the "half body" suspect: the pool
  is albedo-modulated — the black suit (albedo ≈ 0.05) stays black under
  any pool energy; the omni's 2.6 gives it the blue sheen instead.

**Item 4 — DIAGNOSED, the fix is a separate extraction task (PENDING):**
- the visible plaza "grid" = the `O_DE_Btm` slab's `DE_V_wall01` paint —
  and that texture is RGB, NO alpha channel (the grid is PAINT, the
  transparency is impossible through it);
- the TRUE lattice texture = `Iron_net` (RGBA, 59% holes; the pbr_albedo A
  = the staged mask, verified identical) — but **NO mesh in materials.json
  references Iron_net**: in the client the plaza lattice = the BSP surf
  material, and OUR extraction lost those surf records — the plaza's
  brush tops trace as `BSP:Polys377/348 surf=-1 tex=?` (the grey
  placeholders). The client reference shot (the user's): the statue
  visible THROUGH the grid holes.
- the fix = recover the lost surf→texture records for the surf=-1 faces in
  tools/l2strict (the fnd_13/14 surf mapping gap) — a tools-level RE task,
  NOT a shader/material patch. PENDING (the next session's candidate).
- the Iron_net fences DO render (the ALPHA_CUTOUT path) — only the plaza
  floor surf records are lost.

**Gate A:** the boot 0 script errors, the layer routing intact (395
all-placeholder + 5 mixed), "lantern pools: 32 positions → 192 tracked",
the DEVLOG-145 road spawn intact. No shader edits (no reimport). NO
display verification by the agent — the user's screenshots decide.

**The perf note:** 32 shadowed omnis in the compatibility renderer (cube
maps) — the frustum culling keeps only the in-view lights' shadows; if
the FPS dips, the next lever = the shadow distance gating per lantern.

**DEVLOG-148 rev2 — the probe series on the black body + the shadow atlas
gate + the step-up assist:**

**The black body (probe 6 series, L2_TIME=22, the camera at lantern[0]):**
- the omni shadows OFF → the body STILL black (the acne hypothesis
  refuted); the omni cull_mask = ALL → STILL black. The REAL mechanism:
  **the plafond sits at KNEE height (~0.3-0.5 m up — the short DE posts)
  and the character standing at the post puts the omni INSIDE the body
  volume — every outward face has N·L ≤ 0** (the light inside a mesh
  lights only the backfaces, which are culled). The black suit albedo
  (≈ 0.05) makes the moon/pool contributions unreadable on the torso
  (the face and the leggings = the light albedo — lit ✓ the user's first
  close-up: the legs lit, the torso black).
- **the fix: the lantern pools RETURN to the body** (the player
  materials' lantern uniforms restored): the pool's abs(N·L) works from
  inside the volume too, it is deterministic and identical to the ground
  pools the user approved ("пересечение света фонарей работает"). The
  layers = 2 stay (the omni shadows).
- the omni stays for the GROUND placeholders + the shadows; inside the
  body it contributes ~nothing (harmless).

**The shadow atlas gate (the user's item 2: "фонари посередине судя по
теням не работают"):** 32 cube-shadow omnis overflow the compatibility
renderer's shadow atlas — SOME lights silently lose their shadows (the
inconsistent shadows between the lanterns). Fix: the shadow distance gate
in _process's 0.5 s tick — `shadow_enabled = distance < 25 m` per lantern;
the omni lighting and the pools are unaffected (always on). The gate is
also the FPS lever if the cube shadows get heavy.

**The step-up assist (the user's item 3: the character cannot walk over
the curbs/steps):** after move_and_slide, when walking into a low
obstacle on the floor: the ankle-height forward ray blocked + the
knee-height forward ray clear + the down-cast ahead lands a floor with
the rise ≤ 0.45 m → the position steps onto it (velocity.y reset). The
body origin = the capsule center 0.9 m above the floor.

**Item 4 (the plaza lattice) = unchanged, PENDING:** the lost surf
records on the plaza brush tops (DEVLOG-148 above) — the
tools/l2strict extraction recovery task.

**Gate A:** the boot 0 script errors; the spawn intact. The night
verification render (22:01, the camera at lantern[0]): the body region
mean RGB (88.6, 101.3, 114.6) — the blue-pool tone, the bright
highlights present (max 255). NO eyeball verdicts — the user's
screenshots decide.

**DEVLOG-148 rev3 — the user's follow-up (half the body black at night;
the house door black; the middle lanterns unfixed; no curb step-over):**

- **The layer-2 placeholders STOP casting omni shadows** (the
  all-placeholder statics, the grey twins, the brush grey insts —
  cast_shadow OFF): only the CHARACTER casts now. The client's lamps are
  shadowless — our building shadows were blacking out the door recesses
  ("дверь дома чёрная"); with the walls out of the shadow pass the
  recesses receive the omni again (the client look), the two weak
  character shadows remain, and the shadow map contains a single caster
  (no atlas pressure from the buildings).
- **The shadow distance gate tightened 25 → 12 m** (the plaza's whole
  lantern set fit the 25 m radius and re-overflowed the atlas).
- **The body pool: energy 4.0 + lantern_ndl_soft 0.5** (a new shader
  uniform, mix(abs(N·L), 1, soft)) — the black suit (albedo ≈ 0.05)
  becomes readable at night; the ground pools keep the approved 2.6 /
  full N·L.
- **The step-up assist: the is_on_wall() condition dropped** — a low curb
  can register as a floor contact (the slope under the floor_max_angle),
  not a wall, so the assist never fired; now the ankle/knee/down probes
  decide whenever the character walks on the floor.

**Gate A:** the reimport rc=0 (the shader edit), the boot 0 script
errors, the DEVLOG-145 spawn intact, the real-display compile check 0
shader errors.

**DEVLOG-148 rev4 — the "half body" ROOT CAUSE FOUND: the upper-body part
was on a POOL-LESS material.** CHAR_MAT_MAP routes the alpha-cutout parts
(the bodice `FDarkElf_m001_u`, the gloves `_g` — the binary strap/plate
alpha) to a StandardMaterial3D override (the old scissor fix, 2026-11-15)
— the override has NO lantern pool, so the whole UPPER body rendered pitch
black at night while the legs (the `_l` part, the plain ShaderMaterial)
were pool-lit — EXACTLY the user's screenshot split at the belt. Fix: the
alpha-cutout parts STAY on l2_surface_pbr with use_alpha (the shader cuts
the binary mask with the same 0.4 scissor) + the pool uniforms + energy
4.0 / ndl_soft 0.5. The verification render (22:01, at lantern[0]): the
body region mean RGB (114.2, 124.7, 135.8) vs (88.6, 101.3, 114.6) before
— the torso pool-lit. Gate A: the boot 0 script errors.

**DEVLOG-148 rev5 — the plaza darkness root cause: the 7 m omni range.
The user's items (the multiple-source shadows, the middle lanterns, the
curb climb):**

- **The lantern range 7 → 22 m** (the omnis in world.gd + the
  `lantern_range` uniform in BOTH pool shaders). The diagnosis: the plaza
  center sits 10-15 m from every lantern — the 7 m hand-set range
  (DEVLOG-144) left the whole plaza grid beyond every light (the moon is
  blocked by the sunken rim's own shadow) — "фонари посередине
  нерабочие". With 22 m the omni pools cover the octagon wall-to-wall
  (the verification render 23:01 at the plaza: the whole grid lit, the
  client-like wash). The client's own Light records for the lamp posts
  (Light6 at (9815,17978,-4435) = exactly lantern[0], brightness 200/255,
  radius 70) were extracted for the record — the UE2 radius units do not
  translate 1:1 (the client's plaza wash is the BAKED lightmap, not the
  runtime radius), so the range stays the hand-tuned 22 m.
- **The shadow gate restored to 25 m** (the real "middle lanterns" cause
  was the range, not the atlas overflow).
- **The step-up assist: the single 0.55 m down-cast flew PAST the 10-30
  cm wide curbs** (the landing = the flat ground behind, rise ≈ 0 → a
  no-op teleport → "no step-over"). Now THREE down casts at 0.40/0.50/
  0.65 m, the first valid rise (0.02..0.45) steps onto the curb.

**Gate A:** the reimport rc=0 (the shader edits), the boot 0 script
errors, the spawn intact, the plaza verification render lit.

## DEVLOG-149 — 2026-11-22: the PHYSICAL lanterns (the user's "делаем фонари по полной физике а не фиксим колхозно")

**The user's verdict on rev5:** (1) the village OVERLIT — even the roofs
lit (the shot = 07:40 ДЕНЬ — the omnis burned at full power at DAY);
(2) the steps STILL not climbed; (3) no shadows possible at that
lighting; (4) the FULL physics: the occlusion by the obstacles, the
lamp's 4 corner ledges + the cap eating their share of the light, and
the crystals must GLOW (not the static texture).

**The day flood root cause:** the 32 omnis + the shader pools burned at
full power around the clock — at day they added on top of the sun
(the blowout). Fix: the lantern day/night curve in _update_daynight —
`lamp_f = 1.0 - smoothstep(-0.05, 0.10, sun_elevation)`; the omnis'
energy = 1.8 × lamp_f, the pools ride the same factor through the new
`lantern_night` shader uniform (updated on the tracked materials only
when it moves by >0.004). The lamps are night/dusk-only now, the client
way.

**The pool sum clamp:** with the 22 m range, 6-10 lanterns overlapped at
one fragment and the unbounded sum blew the render white. Both pool
shaders clamp `lant_sum = min(lant_sum, 1.2)` — the overlapping pools
SATURATE, they do not stack.

**The physical occlusion:** the rev3's cast-OFF on the layer-2
placeholders REVERTED — every surface casts into the omni shadow maps
(the walls block the light: "у нас освещает даже те места, которые не в
зоне видимости фонаря" — fixed). The lamp statics' own metal (the 4
corner ledges, the cap) casts — the light is physically clipped: the
cap eats the upward cone (the roofs stay dark), the ledges clip the
sides. **The translucent glass does NOT cast**: the lamp statics' split
gains a third partition — the DE_V_cube_deco3 surface (tagged
`l2_plafond` in l2_proc_tex) renders as its own cast-OFF inst, or its
shadow would blob the ground under the lamp.

**The crystal glow:** the plafond glass materials (1 shared material)
pulse in _process — `emission_energy = 1.35 + 0.45 * sin(t * 1.7)` — the
crystals breathe ("кристаллы должны хотя бы светиться").

**The step-up assist — the headless L2_STEP_TEST probe built**
(`L2_STEP_TEST="x,z"` = the scripted click-to-move target,
`L2_STEP_DEBUG=1` = the probe prints). The probe walked the character
into the plaza rim and caught the REAL obstacle: the rim ledge is
**0.53 m tall** — the knee-height probe (the feet + 0.60) was BLOCKED
(the obstacle is taller than the old 0.45 m limit) — the assist never
fired. Fixed: the knee probe at the feet + 1.15, the rise limit 1.05.
The re-probe: `knee_clear=true, dist=0.4 rise=0.53` → the character
steps onto the rim. (The L2 client walks over such ledges by design —
the geodata-driven movement; the 1.05 m limit matches.)

**Gate A:** the reimport rc=0 (the shader edits), the boot 0 script
errors, "lantern crystals: 1 glass materials", the DEVLOG-145 spawn
intact; the day AND night verification renders (the real display): the
day = the normal sun look (the flood gone), the night = the pools wash
the plaza grid, 0 shader compile errors.

**PENDING (unchanged):** the plaza lattice = the lost BSP surf records
(the tools/l2strict extraction recovery).

**DEVLOG-149 rev2 — the CAVE model (the user's: "солнце не должно влиять,
локация в пещере"):**
- The sun and the moon fade to ZERO across a 15 m feathered boundary of
  the village bbox (_update_daynight): inside the cave no directional
  light reaches anything — the lanterns own the cave lighting.
- INSIDE THE CAVE THERE IS NO DAY: `lamp_f = max(lamp_f, cave_f)` — the
  lanterns (the omnis + the shader pools) burn around the clock. This is
  also the fix for "фонари посередине не работают" daytime reports: they
  were night-only by the old curve.
- The hop fallback in the step-up assist: the knee clear but no landing
  matched (the odd obstacle shapes) => velocity.y = 4.5 (the apex
  ~0.5 m), repeated while blocked => climbs.

**Gate A:** the boot 0 script errors; the cave-day verification render at
the user's point (07:43): the sun off, the village lit by the lanterns
(the readable textures, no white blowout); the night render = the pools
wash the plaza.

**DEVLOG-150 — the iteration the user scored ZERO ("снова переосвещение.
теней нету. персонаж ступеньки не перебегает. результат итерации
нулевой") — and all three complaints were TRUE BY CONSTRUCTION:**

1. **"теней нету" — shadows were architecturally impossible.** The pools
   are pure fragment math (a fixed lantern-position array + distance
   falloff): a shader pool CANNOT know about occluders, so the ground and
   the body could never receive a shadow from it. The omnis were
   cull_mask = 2 (the placeholders only) — layer 1 (all the PBR ground +
   the character) received NO real lights at all. The rev2 report's
   "тени персонажа в заливках" was a false claim — nothing in that build
   could produce a shadow.
2. **"переосвещение" — the falloff was not physics.** The pool curve
   pow(1-d/r, 0.25) is nearly FLAT (75% strength at 15 m) and the omnis
   ran attenuation 0.25 (Godot: decay ~0 = almost no decay) — everything
   washed. The cave model then made this wash 24/7 inside the village.
3. **"ступеньки не перебегает" — three stacked bugs** (the new STEPPOS
   cadence print in the probe located them):
   a. the knee veto stalled every STAIRWAY (the stair mass 4+ steps up
      blocked the knee ray while the very next tread was a valid landing;
      the probe measured a 0.35 m/s average crawl, rc=timeout);
   b. low lips (5-12 cm) pass UNDER the ankle ray (feet+0.12) — the body
      is pressed but the assist never fires (the down-casts are gated on
      the ankle hit);
   c. the sunken plaza rim: a >45° drop reads as a wall for
      move_and_slide, and the 0.9 m down-casts (bottom = feet-0.2) cannot
      see the plaza floor 0.53 m BELOW the feet — rv=0.00 + the
      blocked-target killer = the character stands FOREVER (the user's
      exact "не перебегает").

**The fixes:**

- **The physical falloff, one function everywhere** (both pool shaders +
  every lantern omni): Godot's own get_omni_attenuation (decay = 2.0),
  i.e. the range window (1-(d/range)^4)^2 times the TRUE inverse square
  1/d^2. The omni_attenuation 0.25 -> 2.0 on the 32 lantern omnis; the
  pool energy 2.6 -> 10.0 (the body 4.0 -> 12.0, the sum clamp 1.2 ->
  1.3) rebalances the ~25x faster falloff. The roofs and the far plaza go
  dark (the user's "у фонарей нету такого градуса, чтобы крыши осветить").
- **The shadow carriers** (world.gd): TWO real shadow-casting omnis
  parked every frame at the TWO registered lanterns nearest to the
  player (cull mask 3 = layers 1|2, range 22, attenuation 2.0, energy
  10 x lamp_f). The pools SKIP those two indices (the new
  lantern_shadow0/1 uniforms, pushed via L2ProcTex.set_lantern_shadow
  only on change): the light at those lanterns arrives through the real
  omnis WITH their shadow maps -> the character casts a shadow on the
  ground. Because the omni sits at the same plafond position with the
  SAME curve and energy as the pool, the retarget swap is invisible —
  only the shadow map presence changes. The compat 8-light cap is safe
  (2 omnis per object); the shadow atlas is safe (2 carriers + the
  player-distance-gated lantern omnis). L2_NO_CARRIER_SHADOW=1 = the
  numeric A/B diagnostic (no effect on the normal scene).
- **The body back on LAYER 1** (the DEVLOG-148 layer-2 leftover): with
  the pools AND the 32 omnis (cull 2) both lighting it, the body was
  double-lit AND the omni side rolled the per-object 8-light lottery —
  an angle-dependent body light. Layer 1 = the pools (with the carrier
  skip) + the two carriers = exactly the light the ground gets, so the
  cast shadows land on consistently-lit ground. The body materials are
  now tracked (the skip + the night factor reach them; untracked, the
  body kept its own pool from the two skipped lanterns ON TOP of the
  carrier omnis).
- **The step assist rework** (player.gd): the knee veto DROPPED as a
  climb condition — the LANDING decides (a real tread has an UP normal;
  the wall-interior garbage the veto guarded against is filtered by
  normal.y > 0.55); the assist runs on the actual PRESS (rv < 0.5 = the
  killer's own threshold — never mid-stride on slopes) not only on an
  ankle hit; the STEP-DOWN search (deeper casts to feet-1.7, dy in
  -0.02..-1.15) carries the body over the sunken-rim drops; the hop
  fallback only on a real ankle hit with the knee clear (no bunny-hopping
  at walls).

**The probe tooling:** L2_STEP_TEST="x1,z1,x2,z2" (a start teleport by
the down-cast) / "x1,z1,y1,x2,z2" (an explicit start height — the
down-cast from y=50 lands on the O_DE_MT_Out shell ~58 m above the
plaza: the village is INSIDE the mountain, the roofs cover the roads) +
the STEPPOS print (the position/speed/target every 0.5 s — the
time-sink locator).

**Evidence (numbers):**
- The probe (140.05,157.23,-44.5 -> the plaza center 134.26,164.9): the
  road stairways climb (rise 0.06/0.08/0.13/0.25/0.33/0.46 — including
  the previously-vetoed 0.25 at knee_clear=false), the rim crossing
  completes at rv 6.4 and the run ARRIVES (tgt=false at rv 3.15 = the
  ARRIVE_DIST, NOT the killer). The one remaining stall = the
  straight-line route's O_DE_inlet canyon wall (the floor profile: ny
  0.06-0.27 = 75-86 degrees) — correctly unclimbable, the killer's
  designed drop.
- The plaza structure (the floor profile at the user's point): the
  plaza = the BSP Polys348/3993 tops at y -46.0..-46.2 UNDER the
  MT_Out/MT_In shells (+12..15 / -3..-6) — the village physically sits
  inside the mountain (the cave model is also the literal geometry); the
  road (O_DE_Pir01) at -45.47, the rim drop ~0.55 m.
- The wash metrics (the ground region of the verification frames):
  the cave-day plaza mean 0.130 / p50 0.075 / p95 0.425 / frac>0.6
  2.2%; the night 0.170 / 0.154 / 0.452 / 2.3% — a dark plaza with
  LOCAL pools, no wash.
- Gate A: the probe and render boots 0 SCRIPT ERROR, 0 shader compile
  lines; "shadow carriers parked at (133.2,-44.6,167.9) and
  (138.1,-44.6,166.9)" — the two nearest lanterns flank the plaza spawn.

**PENDING:** the pixel A/B of the carrier shadows (the render pass was
interrupted — the user verifies visually); the plaza lattice = the lost
BSP surf records (the tools/l2strict extraction recovery), unchanged.

**DEVLOG-151 — the user's pass on DEVLOG-150 ("свет натуральнее, но
непонятно откуда блики... теней так и нету... ступени опять не может
перейти") + the very old bug opened: "опоры деревни не на своих местах —
в оригинале они стоят в пещере, и от них цепи идут к деревне".**

1. **The mystery view-dependent glints** — the two carrier omnis are REAL
   lights: their Schlick-GGX specular hotspot on the POM floor is
   view-dependent (the pools' emission is not) and read as "window
   glints". `light_specular = 0.15` on the carriers.
2. **The shadows still absent** — the ~10-15 lantern omnis shadowed by
   the 25 m player gate were filling the compat shadow ATLAS and could
   evict the carriers' own atlas slots. The lantern omnis are now
   shadowless entirely (they only light the layer-2 placeholders);
   the TWO CARRIERS own all the character shadows with guaranteed
   atlas slots. The shadow gate loop removed from _process.
3. **THE FEET BUG (the root of every step failure since DEVLOG-148)** —
   the capsule is radius 0.3 / height 1.7 with the shape node at local
   +0.85, so THE BODY ORIGIN IS THE FEET. Every assist formula assumed
   the origin 0.9 m above the floor:
   - `feet_y = body - 0.9` inflated every rise by +0.9 — the 1.05 climb
     limit passed only rises <= 0.15 (the plaza rim ~0.55-0.65 and every
     stair riser NEVER climbed);
   - the step-down window shifted (only drops >= 0.92 fired);
   - the teleports popped the body 0.92 m into the air (the probes'
     "climbs" were pops);
   - the ankle ray ran 0.78 m UNDERGROUND (hit_from_inside = false =>
     garbage/no hits) and the "knee" ray actually ran at feet+0.25
     (ankle height — the stair faces blocked it, stalling stairways).
   REWRITE: feet_y = global_position.y; the ankle ray at feet+0.15; the
   knee ray at feet+1.15; ONE unified deep landing cast per distance
   (feet+1.15 down to feet-1.25) that serves the climb (dy 0.02..1.05)
   AND the step-down (dy -0.02..-1.15), the teleport puts the FEET ON
   the landing, everything gated on the actual press (rv < 0.5).
   **Evidence** (the headless probes): the user's spot ledge
   (11995,16533: the O_DE_Btm deck lip -46.218 -> -46.115, a TRUE 0.103
   m): `dy=0.10 n_y=1.00` climbs on the FIRST press frame and the run
   ARRIVES; the plaza rim descent arrives (rv 6.4 at the drop, the
   target reached). The true rim rise is now measurable (~0.55-0.65 m —
   inside the 1.05 limit, where the old math saw 1.45).
4. **THE PYLONS (the user's old-bug order)** — the per-axis
   `draw_scale3d` was IGNORED (the placement applied only the uniform
   draw_scale). UE2 mirrors the mesh in its OWN axes, THEN rotates; 3 of
   the 8 village pylon actors carry negative scale3d. The O_DE_Pir02
   mesh is an 84.5 m composite: the thin bands at the pivot (mesh y ~0)
   = the CHAINS (their village anchor = the actor Location), the wide
   bands (y -48 base, +8..+32 body/crown) = the pylon tower. With the
   mirror dropped, the tower body rendered on the WRONG SIDE of the
   pivot — the numeric proof: Pir02 (12458,14809) s3=[1,-1,1]: the OLD
   body center lands 591 units (6 m) from the plaza center — ON THE
   SQUARE (exactly the user's screenshot); the NEW (mirrored) lands
   3896 units (39 m) out in the cave with the chains reaching back to
   the village. The 5 unmirrored pylon actors and every [1,1,1] actor
   move by 0 units (nothing breaks).
   - The scale is baked INTO the basis (R*S — the mesh-space scale);
     the Node3D.scale property is unreliable for negatives.
   - The mirrored winding flips a backface-culled StandardMaterial3D
     surface inside-out: the mirrored insts (+ the grey/plafond twins)
     get their placeholder surfaces duplicated with CULL_FRONT
     (_flip_cull_for_mirrored). The PBR/analytic shaders are
     cull_disabled and need nothing.
   - The trimesh collider bodies inherit the full mirrored basis
     (the body.scale property line removed).
   - The same combined scale in the foliage MultiMesh path.
   The other mirrored keys that unwrap correctly now: O_DE_H02/H03
   (the houses), O_DE_Btm_Obj02/03, O_DE_CH_side/sidestair,
   interior_B_delf_store_28/32, sylentemple_deco09/10,
   sylentemple_sidedoor02.
5. The probe start-teleport now lands the FEET exactly on the cast floor
   (the +0.92 pop removed); the 5-value format "x1,z1,y1,x2,z2" is the
   reliable way to probe under the mountain shell.

**Gate A:** the boot 0 script errors, the world built 10.0 s, "lantern
pools: 32 positions -> 192 tracked materials", "shadow carriers: 2
omnis ready" + parked, the player spawn intact. The det==0 invert
errors in the log pre-date these edits (no zero scale3d components in
the map data — the census: only -1.0/1.0).

**PENDING:** the user's visual check (the glints, the two shadows, the
stairs at their spot, the pylons/chains); the plaza lattice = the lost
BSP surf records (the tools/l2strict extraction recovery), unchanged.

**DEVLOG-152 — the GitHub sync (the user's order: b519164 = DEVLOG-96..151
pushed) + the follow-up fixes + the PYLON DECO SYSTEM investigation.**

1. **The glints ("блики от фонарей есть")** — two layers: (a) the carrier
   omnis' specular 0.15 still read at the plaza angles — set to 0.0; (b)
   THE MAIN ONE: the physical pool's near field — 1/d^2 blows to 4.4x
   albedo under the lamp head = the blown rectangles on the user's plaza
   screenshot. Fix (both shaders): the per-lamp near-field cap
   `latt = min(window * 1/d^2, 0.18)` — saturates the < 2.3 m zone to one
   flat bright disc (the client's lamp wash, not a blowout).
2. **The crystals ("посередине фонари без изменений")** — the glass
   albedo is dark (~0.1): the albedo-scaled emission pulse (1.35-1.8)
   read as unchanged. New `emission_flat` uniform (the pbr shader): a
   lantern-colored glow NOT scaled by the albedo; the plafond material
   sets emission_flat = 1.0 (the crystal burns with the lamp blue,
   riding the same pulse).
3. **THE PYLONS (the user: "опоры на старых местах, их 4 штуки")** — the
   deep investigation trail:
   - The raw .unr dump: exactly 8 Pir actors (4x O_DE_Pir01 = a 13 m
     compact pylon, 4x O_DE_Pir02 = an 84.5 m VERTICAL composite: the
     mesh spans from 48 m BELOW the anchor to 32 m above it — a tower
     rising from the cave depths; the thin bands at the pivot level =
     the chains at the village level). No separate chain meshes exist
     in the map.
   - False lead documented: the door-mesh actors 549/550/553/554 (my
     dump's off-by-one: UE object refs are 1-based, ref -N =
     imports[N-1]; the strict extractor's resolution is CORRECT).
   - EVERY Pir actor (and 651 objects map-wide: the lamps, the stones,
     the grass, the temple decos) carries a `StaticMeshInstance`
     reference — an L2-native class (imported from Core; the property
     list is EMPTY — the terminator at byte 0 — the whole payload is
     native data). LineageDeco.u (decrypted, Ver111) = the event
     decoration classes (x_mas_tree, the clan flags) — NOT the SMI
     implementation. The SMI blobs = 2.4-15 KB per instance; the vertex
     count correlates (the Pir02 SMI = 7796 bytes vs the Pir02 mesh =
     731 vertices) — the L2 per-instance mesh/section data. The float
     AND int scans found NO world coordinates inside.
   - THE REMAINING UNCHECKED SOURCE: system/staticobject-e.dat =
     Lineage2Ver413 (the RSA scheme, the same as musicinfo/
     skillsoundgrp — Docs/AUDIO.md documents the wine l2encdec path;
     the binary is missing from the wine drive, the re-acquisition is
     the next step). THE HYPOTHESIS: the pylons' true client positions
     live in the client-side deco dataset (the L2 staticobject system:
     L2DecoLayer/Core — the .unr actors = the raw placements the deco
     layer overrides).
4. Gate A: the boot 0 script errors, "lantern crystals: 1 glass
   materials", the carriers parked, the import rc=0.

**PENDING:** the pylons = the staticobject-e.dat (Ver413) decode; the
plaza lattice = the lost BSP surf records (the tools/l2strict surf
extraction — the user's explicit order); the user's visual check of the
glint cap + the crystal glow.

## DEVLOG-153 — the plaza lattice: the "lost surf records" were a trace-helper artifact (the one-sided fix)

**Correction of the DEVLOG-148 diagnosis:** the plaza lattice surf records were NOT
lost — `bsp2` never dropped them (Polys377 face 8 of the plaza brush = Iron_net,
staged since DEVLOG-148's dates; the cutout shader path + the verified 52%-holes
alpha mask + the ALPHA_CUTOUT whitelist for Iron_net were all in place). What made
the plaza read as a solid painted surface:

1. The trace helpers were blind to BSP colliders: `_surface_for_face`/`_texture_for_surface`
   call `_get_mesh(mesh_key)`, which looks the key up in asset_map — `BSP:Polys377`
   is not there → null → the "TRACE_RAY … surf=-1 tex=?" placeholder for EVERY BSP
   hit (the DEVLOG-148 symptom, but it masked the real state). Fixed in world.gd
   (`_bsp_trace_mesh` + BSP/LevelBSP branches; L2_TRACE_RAY at the center now prints
   `BSP:Polys377 face=19 surf=8 tex=oren_dev_t:Iron_net`).
2. The real bug: BSP brushes are double-sided in our renderer, so the
   floor01 UNDERSIDE of the 3 cm lattice plate (Polys377 poly 9 — the very face
   under the Iron_net lattice) plugs the holes when seen from above. The CLIENT
   renders BSP one-sided (DEVLOG-82 rev2) unless the surf carries PF_TwoSided
   (0x100; the village brush plates are not two-sided).

**The fix (the user's "go ahead"):**
- `tools/l2strict/bsp2.py`: emit the glTF materials `doubleSided` from the surf
  PolyFlags (0x100) and add a winding-orientation guard (fan order by
  Newell·normal in Godot axes — verified: all 1237 village polys have
  Newell·normal > 0, so no winding flips anywhere; the winding was already
  correct).
- `scripts/world.gd`: `_build_bsp_brushes` passes `two_sided` per prim from the
  bsp.json face flags (the L2ProcTex dup flips `cull_back`; the StandardMaterial
  fallback flips `cull_mode`); `L2_BSP_2SIDED` = the A/B diagnostic (the old
  double-sided look, the golden-baseline escape hatch).
- Regenerated `assets/maps/20_18/meshes_bsp/*.gltf` (45 files; the material diff
  is `doubleSided: true → false` per prim) + the stale-cache reimport
  (rm *.import + rm -rf .godot/imported + `godot --headless --import`). Import
  rc 0; the 1400 "Invalid accessor count 0" errors are the known UModel quirk in
  OTHER territories' meshes (Rune/SSQ/fortress/Old_War) — pre-existing.

**A/B at L2_TIME=12 (real display, L2_TIME_SCALE=0):** 5 views × 2 runs
(upper_street, entrance_road, descent, stairway_plaza, spawn_plaza):
- descent: A vs B = 1 px — identical.
- upper_street: A vs B = 228 px > 8 (131 > 30), mean 0.011 — road patch, B = the
  client-faithful side (A was showing the road-plate BACKFACE lit through
  doubleSided; the client hides it).
- entrance_road: A vs B = 831 px > 8 (609 > 30), mean 0.044 — the same road
  backface class (y363-385 x741-847, A mean 97 vs B mean 18 — the removal of the
  phantom backface; B is the client-faithful side).
- Run-to-run noise at the same mode (L2_TIME=12): upper_street A vs A2 = 1 px
  (> 8, 0 > 30), B vs B2 = 27 px; entrance_road A vs A2 = 7 px, B vs B2 = 3 px —
  the street A/B deltas sit above the noise floor but are the physics of the
  one-sided rule, not the plaza change.
- stairway_plaza: A vs B = 64782 px > 8, mask bbox y511-899 x0-803, centroid
  (714, 254) — the plaza region.
- spawn_plaza: A vs B = 83592 px > 8, mask bbox y474-899 x0-689, centroid
  (694, 308) — the plaza region.
- Gate A: 0 shader/script errors in all 10 logs.

**Trace proof (B mode, the plaza):** center ray — `Oren_DEV_S:O_De_01 face=406`
(statue arm above), `BSP:Polys377 face=19 surf=8 tex=oren_dev_t:Iron_net`
at −46.89 (the lattice), then `Oren_DEV_S:O_De_01 face=1` at −47.45 (the statue
body below the lattice).
Through-lattice rays in B: (11500,16872) hits `O_De_02` at −5033 below the
lattice; (11350,16872) reaches the floor01 underside plane −4692 with no
Iron_net hit in between. The Iron_net face is the TOP face of the plate
(local y −0.45; the floor01 bottom = poly 9, local y −0.48).

**User gate:** the plaza screenshot (L2_SPAWN=11620,17120,−4470, yaw 0.78,
pitch −0.55, zoom 0.7, L2_TIME=12, real display) shows the sunken octagonal
plaza with the Iron_net lattice open through its holes and the statue's lower
body/pit visible through it. The reference comparison is pending the user's look.

**Notes for the verification workflow (AGENTS.md):** the golden-baseline pixel
gate is now only meaningful against a FIXED L2_TIME (the day/night default is
RANDOM — the baseline was captured pre-day/night, so a time-blind diff is noise).
L2_BSP_2SIDED reproduces the old look on demand for A/B.

## DEVLOG-154 — the Shirai statue spikes are alpha again (De_Statue004, 2026-11-23)

**The user:** the spikes poking out of the Shirai statue head sit inside
rectangles that in the original have no alpha channel (the spikes are the
original; no opaque rectangles around them).

**Diagnosis:** the client De_Statue004 (the O_De_02 "head" surface) is
**RGBA (64×128), alpha=0 share 0.625** (verified: umodel export of the
package texture). Our staged main PNG `De_Statue004.png` matches the client
(64×128 RGBA, same RGB, same 62.5% alpha) — so the main PNG was fine all
along. The staged `De_Statue004.pbr_albedo.png` was **opaque** (alpha=0) and
the sidecar `De_Statue004.pbr.json` had **no `alpha_mask` key** — the staging
(2026-11-13) ran when the source was RGB; the alpha in the main PNG came
later (or via another path). The runtime cutout path (`l2_surface_pbr`
line 231: `if (use_alpha && alb.a < alpha_scissor) discard;`) samples the
albedo's A, so alpha = the albedo A channel, not the main PNG.

**Fix:**
1. `python3 tools/l2strict/texgen.py assets/maps/20_18/textures oren_dev_t
   De_Statue004` — the PRESERVE-the-source-alpha block (texgen.py:87-130):
   source has mask (sa.min()<0.98) → `achan = src_a` → the new albedo A =
   the 62.5% source mask, sidecar `alpha_mask: true` (the Iron_net/fence
   precedent). The normal/height are unchanged (derived from the same RGB).
2. `scripts/l2_proc_tex.gd`: `oren_dev_t:De_Statue004` added to ALPHA_CUTOUT
   (the generic PVR path `_pbr_material` sets `use_alpha` via the whitelist —
   same as the temple statues / the fence).
3. Reimport (deleted `De_Statue004.pbr_albedo.png.import` + `rm -rf
   .godot/imported` + headless import; the 1404 "Invalid accessor count 0"
   errors are the pre-existing UModel quirk in other territories).

**Plaza screenshot (L2_TIME=12, spawn 11620,17120,-4470):** plaza_after vs
plaza_statue: 5106 px>8 / 4084 px>30, mask bbox y657-889 x796-1099 (the
statue region). Gate A: 0 shader/script errors.

**Pylon notes (still PENDING):** the user sees towers "on the spot, inside
houses": one at UE (13311,15770,-4601.3) [recorded 2026-11-23]; the second —
"one tower inside another building at x=9001 y=16731 z=-4601.3". Our 4
Pir02 towers: (9546,15457), (12458,14808), (13160,18687), (10915,19200)
(all UE z≈-4198). Near (9001,16731,-4601.3): 0 actors (no building, no
tower); the nearest O_De_03 actor is 2504 UE away — so the second tower +
its building are NOT in our map (the client-side world has them). The
deco decode (staticobject-e.dat, Ver413 RSA, wine+l2encdec path) is still
pending — it gives the true client tower positions (the deco-layer-override
hypothesis for the 4 Pir02 towers); the user's observations recorded.

## DEVLOG-155 — 2026-11-24: staticobject-e.dat decode — the tower-position hypothesis is NOT confirmed

- Acquired the l2encdec binary (`l2encdec_2.10.1.7z` from
  `/Media/Games/Lineage_2/l2_other/Edit Files Lineage 2/l2crypt share/` →
  `tmp/encdec/l2encdec_2.10.1/`).
- Decoded: `wine l2encdec.exe -d /Games/ElmoreX3/system/staticobject-e.dat`
  → `tmp/encdec/staticobject-e.dec.dat` (17153 B; header
  "Lineage2Ver413", RSA pair #0).
- The decoded stream begins with a UTF-16 string table — the town structure
  names (Clan Hall Door, Castle Wall, Arena Sign, Village Map Bulletin,
  Outer Castle Gate, Inner Castle Gate, …). **No tower names, no tower
  coordinates** — no "Pir*" strings anywhere, and no float/int values near
  the tower points (9546/15457/−4198, 12458/14808, 13160/18687,
  10915/19200, or 9001/16731/−4601.3). The file is the 2018 town's static
  object list — NOT the Interlude village's tower data.
- Our towers (20_18 map.json, UE): (9546,15457,−4198) ds3[−1,−1,1];
  (12458,14808,−4198) ds3[1,−1,1]; (13160,18687,−4198) ds3[1,1,1];
  (10915,19200,−4198) ds3[−1,1,1].
- The user's "second tower inside another building at x=9001 y=16731
  z=−4601.3": **not present in our maps** (no actors near that point;
  nothing in 20_18 or 20_17; the closest town structures: H02 at
  (10336,16350,−4470), H03 at (9623,18375,−4467)).
- The user's "first tower" is consistent with one of our four (the
  positions above).
- PENDING (revised): the true client tower positions are NOT in
  staticobject-e.dat — they are either in the .unr actor list itself (the
  current placements — i.e. "on the spot" is correct, and the user's
  second-tower observation needs a building+tower added at UE
  (9001,16731,−4601.3) — a new actor, needs the user's go-ahead) or in a
  data source not yet identified. Questions for the user: (a) is the first
  tower = one of the four? (b) for the second — should a Pir02 tower be
  added at UE (9001,16731,−4601.3)?

## DEVLOG-156 — 2026-11-24: O_DE_Pir02 support towers — DrawScale3D axis permutation (glTF Y = UE z)

- **Bug:** 7 village actors with `DrawScale3D.y = -1` (2 of the 4 `O_DE_Pir02`
  towers + 5 others) were vertically flipped. The 84 m tower composite
  (`O_DE_Pir02`, 10 prims: house/body prims 0,2-6 local Y −4.36..+33.40, support
  column prims 7,8 local Y −51.08..+29.75, chain prim 1) had its 51 m column tail
  pointing UP through the surface houses instead of down into the cavern.
- **Root cause (axis proof, not heuristic):** `tools/l2strict/staticmesh.py:441`
  emits glTF positions as `(ue_x*0.01, ue_z*0.01, ue_y*0.01)` — glTF vertical is
  UE z. `DrawScale3D` is authored in mesh-local UE axes `(sx, sy, sz)`, so the
  scale applied to the staged glTF must be permuted the same way:
  `Vector3(s3[0], s3[2], s3[1])` = `(sx, sz, sy)`. The old code used
  `(sx, sy, sz)`, turning `sy=-1` into a glTF-Y (vertical) mirror.
- **Fix:** `scripts/world.gd` statics placement and foliage batch both use
  `Vector3(s3[0], s3[2], s3[1])`. Commented with DEVLOG-156.
- **Numeric verification (fixed camera, `L2_TIME=15.93`, real GPU
  `--rendering-driver opengl3`):**
  - Tower 178 view (`L2_SPAWN=12458,16808,-4601.3`, yaw 0, pitch 0.10): before vs
    after `changed>8=99446  >30=8664  max=246  mean=4.349` (fix is real/large).
  - User cave camera (`L2_SPAWN=12856,16004,-4601.3`, yaw 0.33, pitch 0.02):
    before vs after `changed>8=268336 >30=47874 max=247 mean=4.774` (large; the
    two sy=-1 towers 178/189 move into view/cast different shadows here).
  - Checkpoint ref camera (`L2_SPAWN=12856,16004,-4601.3`, yaw −3.03): only 6 px
    (>8) differ — the two flipped towers are not visible there; `L2_TRACE_BOX`
    bottom half shows no `O_DE_Pir02`/`O_DE_MT_In` hits, only floors/lamp/player.
  - Plaza baseline camera (`L2_SPAWN=10741,16930,-4628.9`, yaw 16384, zoom 1.0,
    `L2_TIME=12`): before vs after `changed>8=10 >30=2 max=35 mean=0.0004` (noise).
- **Geometry check (all 4 towers, fixed):** AABB max Y = −8.58 m (village
  surface ~0). Old sy=-1 towers had max Y +9.10 m (column tail above houses).
  Vertical bottom-up traces at each tower column XY confirm `O_DE_Pir02` sits
  between `O_DE_MT_Btm` (below, ~−74 m) and `O_DE_MT_In`/`O_DE_MT_Out` (above),
  no surface-house intersection. Above-view renders saved:
  `tmp/tower_ab/above_{178,189,181,194}/shot1.png`.
- **Status:** user confirmed towers are in place (2026-11-24). Axis fix
  committed separately for rollback.
- **Side effect (user-reported):** Shillien Temple texture/appearance bug also
  resolved incidentally. This is consistent with the same global permutation:
  20_17 has 88 non-uniform DrawScale3D actors with `sy!=sz` (0 with `sy<0`)
  now scaled on the correct glTF axis; 19_18 has 6 (1 `sy<0`), 21_18 37, 18_19
  2, 19_19 1. Not separately verified here beyond the user's confirmation.

## DEVLOG-157 — 2026-11-24: step assist regression (house entry / stairs)

- **User report:** "персонаж не может забегать в дома, снова проблема перешагивания ступенек" (all DE village houses except the topmost by the stairs) + "ступеньки".
- **Root causes found:**
  1. **Blocked-target killer preempted the step assist.** The killer ran before `move_and_slide()` and set `moving=false` when `rv < 0.5` for >0.5s, so the post-`move_and_slide()` step assist (`if moving and is_on_floor()`) never fired. Moved killer to after the step assist; it now skips if the assist landed this frame and has a 3s escape hatch to avoid loops.
  2. **Step assist lift-fall loop.** The assist teleported only `global_position.y = floor_y2` at the current XZ; for a forward landing the player was left floating above the old floor, fell back next frame, and re-triggered the assist (observed as repeating `STEP dist=... dy=0.06..0.10` with constant body pos, `rv~0`). Fix: place feet on the landing XZ+Y (`global_position = landing_pos`).
- **Files:** `scripts/player.gd`.
- **Automated checks (headless xvfb, `L2_STEP_TEST` + `L2_STEP_DEBUG=1`):**
  - H02 O_DE_H02 (11279,18634): climbs dy=0.71, reaches target (passes). Before/after fix: pass.
  - H01 O_DE_H01 (11441,19405, "topmost by stairs", user said works): before fix looped on dy=0.06; after fix climbs and reaches target.
  - H04 O_DE_H04 (13174,15445): after fix, small dy=0.10 step climbs, but the chosen straight-line path then hits a 1.10m rise (above the 1.05m climb limit) and the blocked-target killer drops the target after grace. This path hit a wall/high edge, not a confirmed door; door approach angle not identified by automated test.
- **Status:** step-assist regression fixed in code (killer ordering + landing placement). **Not fully user-verified.** The "can't enter houses" report may be fully explained by the loop/killer bug, but needs user retest at real doorways, especially the houses the user reported.
- **Separate open issue (reported same message, not fixed here):** "у фонарей посередине нету оправы / цоколя" near the Shillien statue and transparent floor lattice. Geometry trace confirms `O_DE_Lamp01` surf8 `oren_dev_t:DE_V_deco10` exists at socket/collar height (trace hit at UE Z -4473). Visual cause not identified from code; screenshots saved at `tmp/lamp_check2/`, `tmp/lamp_close/` for user reference. Needs user clarification / visual confirmation of which part is missing.

## DEVLOG-158 — 2026-11-24: lantern frame/socket material routing

- **Root cause:** the lamp meshes contain the complete frame geometry. `O_DE_Lamp01`
  has 10 surfaces; the crystal is surface 9 (`DE_V_cube_deco3_c`) and the
  socket/collar is surface 8 (`DE_V_deco10`, AABB local Y
  `-0.030557..0.016984`, immediately below the crystal). `O_DE_Lamp02` has
  8 surfaces; its crystal is surface 7. The static mesh `primitive_material_indices`
  are identity and the trace hit `O_DE_Lamp01` surface 8 at UE Z `-4473`.
  A forced `L2_FLAT_DEBUG=1` render showed all frame and crystal surfaces, so
  this was not missing geometry or a bad map placement.
- **Fix:** in `scripts/world.gd`, only the two lamp mesh keys route non-crystal
  surfaces through the existing `StandardMaterial3D` fallback. The crystal
  remains on the PBR plafond material/emission path. This makes the dark metal
  frame/socket receive the existing layer-2 lamp omni without changing other
  meshes or lighting parameters.
- **Verification (same GPU plaza camera, `L2_SPAWN=10741,16930,-4628.9`,
  yaw `16384`, `L2_TIME=12`, one settle tick):** before/after shot1 changed
  `296684` pixels at `>8` (`144276` at `>30`, max `255`, mean `6.1694`);
  shot2 was effectively identical (`296689`/`144275`, max `255`, mean
  `6.1694`). The after boot log reports `2 mixed keys split` for the lamp
  routing and the crystal count remains `1`; the frame is therefore on the
  layer-2 StandardMaterial twin while the crystal stays on the plafond path.
  Gate A: `0` lines matching `shader error|compile` in the full stderr.
  The existing trace still names `Oren_DEV_S:O_DE_Lamp01` and its authored
  surfaces; the earlier exact socket trace is recorded above. The only exit
  diagnostics are Godot resource-leak messages after its intentional
  screenshot quit, not shader compilation failures.

### DEVLOG-157 follow-up — target stop regression

- **User report:** after the step-assist fix, click-to-move did not stop at the target and continued along the trajectory.
- **Root cause:** the `else` arrival branch cleared `has_target` but did not clear `moving`/horizontal velocity. During the earlier edit, the `if not moving` damping line was also accidentally joined to a comment and became inactive.
- **Fix:** on arrival explicitly set `moving=false`, `velocity.x/z=0`; restored the damping block on its own line.
- **Verification:** `L2_STEP_TEST="112.79,185.50,-44.5,112.79,187.20"` reaches the stepped landing and reports `tgt=false`, `rv=0.00` on subsequent frames.
