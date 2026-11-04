# Terrain format (Interlude)

> **Legacy reference.** The current, verified implementation is
> `tools/l2strict/terrain.py`; see `Docs/strict-pipeline.md`.

## TerrainInfo (one per map, class TerrainInfo)

Properties (legacy `18_20` dump omitted `Location`; `20_18` and the strict
pipeline parse `Location`, `MapX`, `MapY`, `QuadVisibilityBitmap`, and
`EdgeTurnBitmap`):

| Property | Meaning |
|---|---|
| TerrainMap | OBJECT ref → heightmap Texture (format TEXF_G16=10) |
| TerrainScale | Vector (X=quad size, Y=quad size, Z=height scale/256) |
| Layers[i] | struct TerrainLayer (up to ~11 used) |
| DecoLayers | ARRAY of decoration layers (not used for demo) |
| iLeaf | ARRAY i32, 2048 entries (BSP leaf visibility, unused) |

TerrainLayer fields (nested struct properties):
`Texture, AlphaMap, UScale, VScale, UPan, VPan, TextureMapAxis,
TextureRotation, LayerRotation, TerrainMatrix{XPlane,YPlane,ZPlane,WPlane},
KFriction, KRestitution, LayerWeightMap, Scale, ToWorld[0..3],
ToMaskmap[0..3], bUseAlpha`.

For legacy `18_20`: layers use textures from `T_texture` (Base), `T_oren`
(Obase_1, OG_48/49/51/59_t, OC_03/05, OS_12, OST_11) and alpha masks from
`T_18_20` (18_20_BASE_C, 18_20_G, 18_20_G1..G3, 18_20_C, 18_20_C1,
18_20_R, 18_20_DB). Mask textures are 1024×1024, channel mapping for the
demo: use R channel as blend weight.

## Heightmap texture "18_20" (T_18_20.utx, legacy)

- Properties: Format=10 (TEXF_G16), UBits/VBits=8?? (legacy), USize=256,
  VSize=256, UClamp/VClamp=256, MaxColor.
- Raw u16 LE data: **offset 62** of the object blob, length 131072
  (256×256), followed by u_size(4) v_size(4) u_bits(1) v_bits(1).
- Row 0 is at the tile's MIN Y edge (north), column 0 at MIN X.
- World height: `z = (h - 32768) * TerrainScale.z / 256`
  = (h-32768) * 76/256 for this map → -8474..-835 units.
- l2mapconv formula check: vertex z = h*scale.z + location.z -
  32768*scale.z, scale.z = TerrainScale.z/256 ✓.

## Terrain mesh for Godot

- 256×256 vertices, 255×255... actually 256×256 vertices make 255×255
  quads; L2 renders 256×256 QUADS wrapping (last row duplicates row 0
  tile seam) — for the demo build 255×255 quads (no visible seam inside
  the tile).
- Quad size = TerrainScale.x = 128 units. Tile = 32768 units.
- UV: u = col/256, v = row/256 (mask textures are per-tile 1024²).
- Splat shader: 4 layers (Base, Obase_1 w/ mask BASE_C, OG_48 w/ mask G1,
  OC_05 w/ mask C); tile textures repeat every 128 units (UV scaled by
  256/... see shader), masks sampled at 0..1 per tile.

## TerrainSector (256 objects per map)

Legacy C1-era sub-blocks; NOT required for rendering — skip.

## Hole / surface mask — verified caveat for `20_18`

- `surface_present_u8.raw` is 256×256 quads: `0` = hole (no terrain surface),
  `1` = surface. This comes from `QuadVisibilityBitmap` and carries into the
  verified `20_18` pipeline (`tools/l2strict/terrain.py`, `scripts/world.gd`).
- Hole cells hold placeholder raw 2511 (z ≈ −8821.9 for `20_18`) and must not
  be rendered, collided, or sampled for ground height. They are filled by
  village static meshes that carry their own trimesh colliders.
- L2 renders 256×256 quads per tile (257×257 vertices). Quads whose
  `surface_present` bit is clear are skipped when building the mesh and its
  trimesh collision.
