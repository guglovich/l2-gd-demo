# Engine.dll RE — the findings ledger (the user's directive, 2026-11-17)

Findings that used to live only in chat and were lost. This file is the
durable store; the progressive C reconstruction lives in `tools/re/engine/`
(aim: `100% source` of the reverse-engineered parts).

Ground truth binary: `/Games/ElmoreX3/system/engine.dll` (8 794 112 B,
sha256 `974810cad7f04f80b8ce81ce19c4ad44fbd3447bb6b7c8c27fd90725c22e7e1e`,
x86 PE, symbol-rich MSVC exports). Companion: `Core.dll` (the package
loader, ULinkerLoad RTTI @0x102382c8). Analysis tool: craft-anything
(`analysis/l2-godot.cany`, findings fnd_1..fnd_21 — mirrored here).

Legend: ✔ = reconstructed in tools/re/engine/*.c; ◐ = disassembled, not
yet reconstructed; ✗ = only chat/memory.

## Core.dll

### FCompactIndex @0x1015cfb0 ✔
`??6@YAAAVFArchive@@AAV0@AAVFCompactIndex@@@Z`. Sign = bit 0x80 of the
FIRST byte; magnitude = (b0 & 0x3F) | (continuation << 6), 0x80-marked
continuation bytes of 7 bits. Negatives are NOT -n-1; negative multi-byte
values exist (imports ≥ 64: b0 = 0xC0|low6). All our decoders were fixed
to this (fnd_13).

## UModel

### UModel::Serialize @0x1030cac7 ✔ (validated EXACT on Model500, 2505317 B)
props(None) + FBox(25 B: Min,Max,IsValid BYTE) + 4 dwords + TArrays
(Vectors, Points, Nodes, Surfs, Verts) + NumSharedSides INT + NumZones INT
+ Zones (compact ZoneActor + QWORD + QWORD + FLOAT) + compact Polys ref +
Bounds(25 B) + LeafHulls + Leaves (3 compacts + QWORD) + Lights + INT
RootOutside + INT Linked + Sections (ver≥105, retail form) + LightMaps +
ReadL2ModelLighting + L2MeshRequireEnd == export end.
- FBspSurf file record: Material objref + DWORD PolyFlags + 5 compacts
  [pBase, pNormal, pTextureU, pTextureV, **iBrushPoly**] + Owner Brush
  objref + 16 B plane + float lightmap scale + int(−1). Surfs map to brush
  polys by (Owner Brush, iBrushPoly) — fnd_14.
- FBspNode file record tail (retail): 3 bytes (iZone0, iZone1, NumVertices)
  + 5 fixed INTs [iLeaf0, iLeaf1, iSection, iFirstVertex, iLightMap] — the
  client writes INTs where the UE2 reference writes AR_INDEX.
- FBspSection (file): [compact count][count × 40 B vertex records][trailer:
  INT Revision + compact Material + INT NumNodes + DWORD PolyFlags + INT
  iLightMapTexture — NO CacheId]. FBspVertex in-stream = pos12+uv8+8B
  mystery+normal12.
- Retail node walk: plane 16 + ZoneMask 8 + NodeFlags BYTE + 7 compacts
  + 2 spheres 32 + iZone bytes ×2 + NumVertices BYTE + 5 INTs (iLeaf0,
  iLeaf1, iSection, iFirstVertex, iLightMap).
- **In-memory FBspNode layout (from BuildRenderData): stride 0x14C;
  +0x34 = Nodes data ptr is in the caller... the node record itself:
  +0x18 = iVertPool (first vertex index), +0x56 BYTE = NumVertices,
  +0x60 = iSection (written back by BuildRenderData), +0x100 = DWORD
  (count used by the editor wireframe loop).**
- Model region probe TRAP: surf idx[4] = iBrushPoly (NOT a node index) —
  reading it as a node index produced the fake "zero temple BSP geometry"
  (fnd_15/fnd_21). The node walk = iSurf (node.cs[1]) → surf
  (material/flags/UV axes) + iVertPool (node.cs[0]) + NumVertices.

### UModel::BuildRenderData @0x10307c98 ◐→✔ partial (tools/re/engine/umodel.c)
Groups the runtime Surfs into FBspSections keyed by
(**Material, PolyFlags & 0x2400100, LightMap**). The mask 0x2400100 =
PF_TwoSided | PF_Portal | PF_Mirrored — a GROUPING key, NOT a visibility
filter; all other face flags are stripped at grouping (they cannot gate
anything downstream). Creates FBspSection objects (ctor @0x10311077,
sizeof = 0x34 = 52 B) in the Sections TArray @model+0xE4, appends 0x28-B
vertices per node into section+0x64 array; section fields: +0x18/+0x1C
vertex counters, +0x20 = material, +0x24 = flags&mask, +0x28 = lightmap.
Also reads surf+0x68 (lightmap entry: index * 0xAC into model+0x10C).

### UModel::PostLoad @0x10312cba ✔ (46 instructions, umodel.c)
Iterates the Nodes array only to fix up surf records (sub_1031502d with
&Points[surf.pBase]+0x20); then UObject::PostLoad. **No poly→surf
building** — the runtime does NOT run CSG.

### UModel::Render @0x103064a1 ✗ (partially read)
The wireframe/editor overlay path (FLineBatcher/FCanvasUtil); the game
textured path for models goes through FDynamicActor::Render.

## UStaticMesh

### UStaticMesh::Serialize, L2 branch ✔ (validated EXACT on 27/27 meshes
of sylen_temple_s; tools/l2strict/l2mesh_full.py + umodel.c)
Order after the tagged props (Super::Serialize):
Sections (ver≥112: IsStrip BOOL + 5 WORDs = 14 B) → BoundingBox (FBox 25 B:
Min,Max,IsValid BYTE) → VertexStream (24 B/vert + INT Revision, NO
CacheId) → ColorStream → AlphaStream (4 B + INT each) → UVStreams (8 B/UV +
coord INT + rev INT) → IndexBuffer + WireframeIndexBuffer (2 B + INT) →
CollisionModel ref → collision (2 spans {INT End, compact Count} if the
probe validates, else OldTriangles = 4 FPlanes + AR_INDEX×4 each +
OldNodes = AR_INDEX×4 + FBox 25 B each) → bStaticMeshLod BOOL + LOD01/02
refs → state block (licensee 12=20 B, 14=32, 15..36=36, 37+=40; the
temple meshes carry [0,0,0,1.0,1.0,0,0,0,0]) → INT (the TLazyArray
ABSOLUTE archive offset — ent_main: serial_offset + 89922) + compact
TriangleCount → RawTriangles (36 B verts + INT NumUVs + NumUVs×24 B +
12 B colors + INT MaterialIndex + DWORD SmoothingMask) → InternalVersion
INT → KPhysicsProps ref → AuthenticationKey DWORD (ver≥120) → export end.
- **Section i renders Materials(i)** (Build() asserts
  Triangle.MaterialIndex = SectionIndex, UnStaticMesh.cpp:136).
- The UModel glTF export's primitive order = the non-empty-section order
  (prim vertex ranges == section Min/MaxVertexIndex; empty sections
  skipped). Verified on ent_main (4 sects), skin (20), and by the
  empty-material compression across deco02/04/07, pir, outdeco04...
- FStaticMeshOldCollisionTriangle = 4 FPlanes (64 B) + AR_INDEX ×4 — NOT
  a fixed 16 B record (fnd_6/7/10/11 cover the lazy archive path).

## Actors / level

### ABrush::PostLoad @0x10302ab3 ✔ (brush.c)
Calls AActor::PostLoad only. The Brush actors' own Models are EMPTY
(72 B) in 20_18.unr — the CSG results are baked into the level Model500;
**the client renders nothing from Brush actors** (no runtime CSG exists:
no Csg/Mod/Carve symbols in engine.dll).

### Level BSP surf→polygon mapping ✔ (temple_bsp.py)
Node walk: iSurf (node.cs[1]) → material/flags/UV axes; iVertPool
(node.cs[0]) + NumVertices → the polygon in world coordinates. The BSP
surf flags carry the poly flags through CSG: 0x40a000 faces
(Unlit|0x2000|0x8000 — the zone-boundary faces, 28 with the marker stone
oren_sylen_in002, 111+94 with DE_V_m12/O_dark_01 in the village) and
0x00402000 (Unlit|0x2000) never render; ZonePortal faces =
0x04000109/0x08000109 (PF_Portal|TwoSided|NotSolid|Invisible).

## EPolyFlags (UE2 reference, UnObj.h:236) — the temple-relevant values
0x1 Invisible, 0x8 NotSolid, 0x80 FakeBackdrop, 0x100 TwoSided,
0x2000/0x8000 = PF_Unused2/3 (L2 repurposed), 0x400000 Unlit,
0x4000000 Portal, 0x8000000 AntiPortal. The L2 zone-marker combination
0x0040A000 = Unlit|Unused2|Unused3; the ZonePortal combination
0x04000109 = Portal|TwoSided|NotSolid|Invisible.

## Terrain
QuadVisibilityBitmap: surface_present == 0 = the quad is not rendered.
The VILLAGE holes hold the void placeholder raw 2511 (z ≈ −8821.9); the
TEMPLE footprint holes hold a REAL height (−3753, the plateau the temple
is carved into) — the hole is covered by the temple's own BSP walls and
floor meshes in the client.

## Files of this ledger
- `tools/re/engine/umodel.c` — UModel::BuildRenderData / PostLoad / the
  section grouper (from the 2026-11-17 disassembly).
- `tools/re/engine/brush.c` — ABrush::PostLoad / the brush-render facts.
