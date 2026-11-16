# The Temple Zone Markers (the legacy zone-separator inventory)

The legacy client marks its zones (sound, lighting, ambience) with
INVISIBLE brush volumes and portal planes inside the map. They never
render — `tools/l2strict/temple_native.py` excludes them by name
(ZONE_MARKER_BRUSHES) and by flag (0x40a000 = NoOcclude|Translucent).
This log keeps their coordinates for the future lighting/sound stage:
these volumes define WHERE the client switches zone properties (the
temple interior ambience vs the outside valley), so they are the natural
anchors for our own Godot Area3D sound/light volumes.

All coordinates are game units (UE x, y, z). Source: `20_18.unr` Brush
actors (CsgOper and the FPoly/Polys data), verified 2026-11-16.

## Zone-marker brush volumes (never rendered)

| volume | location | world bbox (X / Y / Z) | flags |
|---|---|---|---|
| Polys17 | (26528, 10388, 16871) | 26328..30512 / 10528..11536 / −4270..−2999 | 0x40a000 |
| Polys23 | (26528, 10400, −3102) | 26400..29184 / 10248..10528 / −4270..−3294 | 0x40a000 (one 0x0 face) |
| Polys28 | (26528, 11664, −3102) | 26400..29184 / 11536..11816 / −4270..−3294 | 0x40a000 (one 0x0 face) |
| Polys55 | (28016, 9364, −4008) | 27880..28280 / 9240..10248 / −4270..−3182 | 0x40a000 |
| Polys67 | (28416, 12964, −4008) | 27880..28280 / 11792..12824 / −4270..−3182 | 0x40a000 |

Reading: Polys17 = a long box along the temple's central axis (the main
hall zone). Polys23/28 = two slabs flanking the hall north and south (the
gallery zones). Polys55/67 = the boxes wrapping the south and north stair
corridors (the entrance-corridor zones). Their material is the same
`oren_sylen_in002` stone everywhere — the texture is meaningless; the
volumes are markers.

## Zone portal planes (never rendered, texture = ZonePortal)

| plane | location | world bbox | faces the direction |
|---|---|---|---|
| Polys115 | (26376, 11017, −3656) | X 26376 / Y 10695..11339 / Z −4377..−2935 | west (the main entrance) |
| Polys123 | (28079, 12817, −3656) | X 27757..28401 / Y 12817 / Z −4377..−2935 | north (the north stair corridor) |
| Polys119 | (28091, 9257, −3656) | X 27769..28413 / Y 9257 / Z −4377..−2935 | south (the south stair corridor) |

These single-face planes sit exactly in the three temple doorways — the
zone borders between the temple interior and the valley. When the
lighting/sound stage opens, each plane is the seam where the interior
zone (dark, reverberant, lamp-lit) meets the outdoor valley zone.
