# ActorX PSA animation format (UModel export)

UModel exports L2 `MeshAnimation` (ver 123 licensee 28) to `.psa` with
`umodel -export` (default ActorX format; `-gltf` refuses animations from CLI).

## Structure (little-endian, all strings NUL-padded 64 bytes unless noted)

```
"ANIMHEAD\0\0\0\0"            (16 bytes)
BONE_NAMES  chunk: "BONENAMES" + count i32 + names[count] (64 bytes each)
BONE_FLAGS? (not in psa — skip)
BONE_HIERARCHY: "BONEHIER" + count i32 + i32(parent)[count]
ANIM_HEAD: "ANIMHEAD"?? — actually named "ANIMHEAD" replaced by:
  "TOTALFRAMES" + i32 frames_total
  "FRAMESIZE"   + i32 frame_size?  (some exporters omit)
"ANIMHEAD" + i32 num_sequences + i32 num_bones + f32 frames_per_sec
SEQUENCE chunk "SEQHEAD"?? — per sequence record:
  name[64], group[64], i32 start_frame, i32 num_frames, f32 rate
  i32 start_bone, i32 num_bones, i32 flags
RAWKEYS chunk "RAWKEYS" + i32 count + keys[count]:
  each key: pos f32[3] (x,y,z), quat f32[4] (w,x,y,z) — ActorX order is
  (x,y,z) pos then (w,x,y,z) quat; quat is Unreal-space (left-handed, Z-up),
  needs -x/-y swap for Godot (Y-up, -Z forward).
```

## Sequences in FDarkElf_anim.psa (Dark Elf female)

Names look like: `wt` (wait/idle), `wk` (walk), `rn` (run), `atk` variants,
`hit`, `sit`, etc. Each sequence = continuous frame range in RAWKEYS.
For movement we need: idle (wt / wt_end), walk (wk / wk_f?), run (rn / rn_f).

## Conversion plan (psa_to_gltf.py)

1. Parse chunks; map bones by name to the glTF skeleton exported by UModel
   (node names match BONE_NAMES).
2. For each wanted sequence build a glTF animation:
   - samplers: rotation (quat xyzw → glTF xyzw) and translation per bone
     (root bone also carries movement).
   - L2 FPS from ANIM_HEAD (usually 32? read actual value).
   - ActorX bones are in **parent-relative** space already (as serialized);
     glTF needs local-space TRS per node — verify by comparing to pose of
     the mesh at frame 0; if mismatch, convert world→local.
3. Embed animations into the character glTF (or a separate .gltf imported
   alongside; Godot merges by node path).

Position conversion L2→Godot: swap Y/Z and invert: glTF pos = (x, z, -y)
in mesh-local space; quaternions: apply (w, x, z, -y)?? — VERIFY
empirically on the character (feet must stay on ground plane).

## Status

`tools/psa_to_gltf.py` — NOT WRITTEN YET. PSA file:
`tmp/umodel_export/DarkElf/MeshAnimation/FDarkElf_anim.psa`.
