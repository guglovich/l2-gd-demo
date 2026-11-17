# The Temple Zone Markers (the legacy zone-separator inventory)

The legacy client marks its zones (sound, lighting, ambience) with brush
volumes. DEVLOG-76 established how they relate to rendering:

- **A Brush poly face renders IFF its FPoly flags are 0x0** (tools/l2strict/
  temple_native.py v6). The 0x40a000 set (NoOcclude|Translucent|Modulate)
  marks the ZONE-BOUNDARY faces and never renders; the ZonePortal faces
  carry 0x4000109. Rendering the marker faces produced the gray in002
  squares and the alien interior walls (the user's reports).
- **The "sky-plane" theory (DEVLOG-72) was wrong**: a brush origin at
  z = +16871 does NOT place the geometry in the sky — the FPoly vertices
  are LOCAL to the brush; Polys17's world Z is −4270..−2999 (the hall).
- **Interior air-air faces never render either** (the load-time carve
  removes them): temple_native v6 computes them automatically as the
  touching planes of two carved volumes (or a carved volume and an ADD
  solid). Manual exceptions for the faces bordering the world's outside
  air: Polys39 poly 0 (the entrance facade), Polys71/59 poly 3 (the
  corridor exits), Polys39 poly 5 (the solid-solid z-fight with Polys43).

This log keeps the volumes' coordinates for the future lighting/sound
stage: they define WHERE the client switches zone properties, so they are
the natural anchors for our own Godot Area3D sound/light volumes.

All coordinates are game units (UE x, y, z). Source: `20_18.unr` Brush
actors, verified 2026-11-17.

## Zone volumes (the world-space boxes of their carved air)

| volume | role | world bbox (X / Y / Z) |
|---|---|---|
| Polys17 | the main hall zone box (ALL faces 0x40a000 — never renders) | 26328..30512 / 10528..11536 / −4270..−2999 |
| Polys23 | the south passage slab zone (5 marker faces + 1 real: poly 1 = the hall wall band, oren_sylen_001_1) | 26400..29184 / 10248..10528 / −4270..−3294 |
| Polys28 | the north passage slab zone (5 marker faces + 1 real: poly 3 = the hall wall band) | 26400..29184 / 11536..11816 / −4270..−3294 |
| Polys55 | the south stair-corridor zone (all marker) | 27880..28280 / 9240..10248 / −4270..−3182 |
| Polys67 | the north stair-corridor zone (all marker) | 27880..28280 / 11792..12824 / −4270..−3182 |
| Polys51 | the apse zone (ALL faces 0x0 — the statue vault renders) | 29144..30464 / 10616..11032 / −4262..−3000 |
| Polys31/35 | the gallery slopes north/south (all 0x0) | 26501..29144 / 11032..11784 and 10280..11032 / −4262..−3000 |
| Polys71/59 | the stair-corridor ramps north/south (all 0x0) | 27888..28272 / 11784..12824 and 9240..10280 / −4262..−3218 |
| Polys39 | the entrance vestibule (all 0x0) | 26328..26501 / 10784..11272 / −3752..−3000 |
| Polys43/63/83/79/87 | the ADD floors and marches (0x0 faces render) | the entrance slabs and the three ai_004 marches |

The static-mesh interior (deco08 = hall floor+walls, skin = the shell,
side_stair = the corridor ramps, deco03 = the apse floor, deco12/11/02 =
the floor plates and wall panels) coexists with these volumes; the brush
faces duplicate parts of it at the same coordinates.

## Zone portal planes (never rendered, texture = ZonePortal, flag 0x4000109)

| plane | world position | faces the direction |
|---|---|---|
| Polys115 | (26376, 11017, −3656) | west (the main entrance) |
| Polys123 | (28079, 12817, −3656) | north (the north stair corridor) |
| Polys119 | (28091, 9257, −3656) | south (the south stair corridor) |

When the lighting/sound stage opens, each plane is the seam where the
interior zone (dark, reverberant, lamp-lit) meets the outdoor valley zone.
