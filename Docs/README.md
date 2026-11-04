# Lineage 2 Godot Fork — Documentation

Fork of Lineage 2 (Interlude-era client data) running on Godot 4.7.
One location — Dark Elf Village, map `20_18` — one playable character
(Dark Elf female), no server, no mobs.

## Document index

| Document | Contents |
|---|---|
| `DEVLOG.md` | **Handoff journal — read first.** Current status, next steps, key facts. |
| `craft-anything.md` | Craft Anything MCP (RE toolkit): project wiring, `native` toolset (Ghidra analog), format limits. |
| `strict-pipeline.md` | **Current pipeline.** `tools/l2strict`, strict gates, output layout, coordinates, verification. |
| `asset-pipeline.md` | Legacy pipeline reference (kept for comparison). |
| `l2-package-format.md` | Binary reference: L2 UE2 package format (decryption, tables, properties). |
| `terrain.md` | Terrain block format, heightmap, layers/masks, world math. |
| `psa-format.md` | ActorX PSA animation format + conversion plan to glTF. |

## Tools

### Current strict pipeline (`tools/l2strict/`)

| Module | Purpose |
|---|---|
| `crypto.py`, `reader.py`, `package.py` | Bounds-checked decryption, compact ints, package tables, references. |
| `properties.py` | Strict StateFrame/property-list parser (arrays, structs, bitsets, legacy `Materials`). |
| `stage.py` | Stage/decrypt only the packages one map needs, with a hash manifest. |
| `extract.py` | Strict map/terrain extraction and exact class-count gates. |
| `materials.py` | StaticMesh surface materials → shader/texture closure. |
| `terrain.py` | Exact heightmap, neighbor borders, visibility, edge-turn, layer UV data. |
| `assets.py` | UModel export, zero-count glTF sanitation, per-map Godot asset staging. |
| `verify.py` | End-to-end verification gates for one exported map. |
| `pipeline.py`, `__main__.py` | CLI orchestration (`build`, `verify`, `extract`, `probe`). |

### Legacy tools (kept for comparison)

| Tool | Purpose |
|---|---|
| `l2_decrypt.py` | Decrypt `Lineage2Ver111/121` packages → raw UE2. |
| `l2_probe.py` | Parse package structure: names, imports, exports, classes. |
| `l2_props.py` | Object data: StateFrame + property lists. |
| `l2_extract.py` | Map extractor: actors + terrain + package deps → JSON. |
| `l2_materials.py` | StaticMesh materials → texture list per surface. |
| `l2_heightmap.py` | Extract heightmap (TEXF_G16) from texture object → PNG. |
| `export_meshes.sh`, `export_textures.sh` | Legacy UModel batch export. |

## Data sources

- Original client: `/Games/ElmoreX3/` (read-only, never modify).
- Strict-pipeline work area: `tmp/l2/20_18/` (regenerable).
- Strict-pipeline Godot assets: `assets/maps/20_18/`.
- Legacy decrypted packages: `tmp/decrypted/` (regenerable).
- Legacy UModel exports: `tmp/umodel_export/` (regenerable).

## External tools used

- `umodel` (UE Viewer, AUR package) — mesh/texture export, `-game=l2`.
- `godot` 4.7.2 (Arch repo).
- Python 3 + numpy + Pillow (Arch repo packages).
