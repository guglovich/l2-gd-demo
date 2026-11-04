# Craft Anything 0.2.0 — project MCP for reverse engineering

Craft Anything (ArtCraft, MIT/Apache-2, pure Rust) is installed system-wide
(`/usr/bin/craft-anything`, `/usr/bin/craft-anything-cli`) with its source
vendored under `tools/craft-anything-0.2.0/` for reference. It is an
investigation toolkit: study any program/game/files from the outside, keep an
evidence-backed memory, optional rebuild-and-compare workflow. Full engine has
298 tools in 17 toolsets (`tools/craft-anything-0.2.0/docs/tools.md`); every
tool is also a CLI subcommand (`craft-anything-cli <id-with-dashes> --json`).

## How it is wired into this project

MCP entry (global `~/.config/opencode/opencode.json`, key `mcp.servers`):

```
craft-anything-cli mcp \
  --project "/home/jinseoyeon/Projects/Lineage 2 Godot/analysis/l2-godot.cany" \
  --deep
```

- `--project` persists investigation memory (brief/plan/findings/evidence
  ledger) under `analysis/l2-godot.cany/` instead of the throwaway session.
  Keep that folder; it is NOT regenerable from tmp/.
- `--deep` = Deep mode (tools may read inside targets). The desktop app's
  global config already has `deep_mode = true`.
- Timeouts raised (startup/catalog 30 s, execution 600 s): Deep-mode Ghidra
  calls take minutes, default 5 s would abort them.
- Only ~35 "Essentials" tools are listed at first; call `list_toolsets` +
  `enable_toolset` to load more (`native` = the RE toolset, 55 tools).
- Restart/reconnect OpenCode after changing the MCP entry.

## Ghidra analog = the `native` toolset

Built-in clean-room engine (works with nothing installed):

| Need | Tool |
|---|---|
| Pseudo-C (Ghidra F5 equivalent) | `native_function_pseudocode`, `native_function_study` (full dossier), `native_functions_decompile` (batch ≤64) |
| Whole binary → pseudo-C files | `native_source_folder_write` (resumable, SHA-256-guarded) |
| Assembly listing | `native_function_disassemble`, `native_function_instructions_list` |
| Function inventory/search | `native_functions_list`, `native_functions_search` (names+imports, regex) |
| Xrefs / call graph | `native_xrefs_list`, `native_name_xrefs_list`, `native_function_references_list`, `native_call_graph_show` (fwd/back), `native_call_path_find` |
| Data flow | `native_value_flow_show` (register def-use) |
| Strings / byte patterns | `native_strings_find`, `native_strings_browse`, `native_bytes_find` (`??`-masked signatures) |
| Headers/layout | `native_layout_show`, `native_sections_list`, `native_library_calls_list`, `native_offered_symbols_list`, `native_address_offset_show` |
| Rename/comment/bookmark | `native_function_label`, `native_names_set`, `native_comment_write`, `native_bookmark_add` |
| Session/overview | `core_target_open` (use `--project`), `core_overview_show`, `core_target_triage` |

Real Ghidra is an optional Deep-mode engine (`/opt/ghidra`, found by
`engines_list` as `analyzeHeadless`); it adds a stronger decompiler and
exotic processors via `language_id`. Second opinions:
`native_objdump_run`, `native_rizin_command_run`, `native_cutter_command_run`,
GDB sessions in the `runtime` toolset, Frida in `frida`.
ghidra-mcp stays registered as fallback; prefer craft-anything (no live Ghidra
instance/plugin needed for the built-in engine).

## Game-format coverage (checked in `crates/formats/src/`)

Supported: UE3/UE4 `.pak` (`game_pak_list/extract`), UE5 IoStore, UE4.26–4.27
cooked textures → PNG, Unity serialized/bundles/IL2CPP, Godot `.pck`, generic
archives (`core_archive_show`, `core_packed_files_list/unpack`).

**NOT supported: UE2 Lineage 2 packages (`.unr/.ukt/.ukx/.usx/.umx`)** — no
L2 readers exist. `tools/l2strict/` remains the only asset-extraction path.
Craft Anything complements l2strict (binary RE, verification), never replaces
it.

## Constraints learned this session

- `/Games/ElmoreX3/` contains only asset folders (MAPS, StaticMeshes, …);
  there is **no `System/` with L2.exe/Core.dll**, so client-binary RE is
  blocked until the user provides the executables. Nothing to analyze natively
  as of 2026-11-02.
- L2 `.unr` etc. are XOR-encrypted UE2 — craft-anything readers will not
  recognize them even if opened; don't waste tool calls on staged packages.
- Findings recorded via `core_finding_record` need evidence ids from the
  ledger (`core_evidence_show`); memory lives in the `.cany` project folder.
- No OpenCode-style "skills" ship with craft-anything; the knowledge base is
  its MCP tools + `AGENTS.md`/`docs/` in the vendored source.

## Planned usage in this project

1. If client binaries become available: open `Core.dll`/`UGame.dll` with
   `core_target_open`, `native_functions_search` for property-name strings
   (e.g. "Rotation", "TerrainScale") via `native_strings_find` → xrefs →
   decompile to confirm UE2 rotation/terrain formulas from code instead of
   screenshot archaeology.
2. `native_bytes_find` for quick byte-signature scans in any L2 executable.
3. Keep the `.cany` evidence ledger in sync with `Docs/DEVLOG.md` conclusions
   (DEVLOG stays the handoff source of truth).
