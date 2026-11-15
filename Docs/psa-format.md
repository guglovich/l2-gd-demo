# ActorX PSA animation format (UModel export) — VERIFIED 2026-11-15

The facts below were verified against the actual FDarkElf_anim.psa and the
UEViewer sources (Exporters/ExportPsk.cpp, Exporters/Psk.h,
Exporters/ExportGLTF.cpp). The earlier version of this doc had the chunk
layout and the quaternion order WRONG — that cost a debugging loop.

## CRITICAL PITFALL (cost the 2026-11-15 session half a day)

The PSA in `tmp/umodel_export/` (Oct 2025) was exported by an OLD UModel
build and contains RAW, NON-NORMALIZED "quaternions" (components like
z=1.0, w=6.47) — that export is UNUSABLE. A fresh UModel export writes
proper normalized quats + full position tracks. ALWAYS re-export the PSA
with the current umodel before debugging the format
(`tmp/umodel_export2/` holds the good one).

## Structure (little-endian)

Chunk header = VChunkHeader: name[20] + TypeFlag u32 (PSA_VERSION =
20100422 on the first chunk) + DataSize i32 (record size) + DataCount i32
(record count) = 32 bytes.

```
"ANIMHEAD"        header only, no records
"BONENAMES"       DataCount = numBones; records = FNamedBoneBinary (120 B):
                  name[64] + flags u32 + numchildren i32 + parent i32
                  + VJointPosPsk (quat 4f + pos 3f + length 1f + size 3f)
                  NOTE: UModel writes parent = -1 for bone 0, 0 for ALL
                  others — the hierarchy is USELESS here; take it from the
                  glTF mesh skeleton instead.
"ANIMINFO"        DataCount = numSequences; records = AnimInfoBinary (168 B):
                  name[64] + group[64] + TotalBones + RootInclude +
                  KeyCompressionStyle + KeyQuotum (4 i32) + KeyReduction +
                  TrackTime + AnimRate (3 f32) + StartBone + FirstRawFrame +
                  NumRawFrames (3 i32)
"ANIMKEYS"        DataCount = Σ(NumRawFrames) * numBones; records =
                  VQuatAnimKey (32 B): pos 3f + quat 4f (X,Y,Z,W — W LAST)
                  + time 1f
```

Keys are FRAME-MAJOR over the whole file: key index for (global frame g,
bone b) = g * numBones + b; a sequence's frames start at
FirstRawFrame * numBones.

UModel applied MIRROR_MESH to the written keys (ExportPsk.cpp:21):
`pos.y *= -1; quat.y *= -1; quat.w *= -1`.

## Conversion to glTF (UModel ExportGLTF.cpp conventions)

The glTF part files (mesh bind pose) use:
- TransformPosition: swap Y/Z, scale 0.01 (UE cm → glTF m)
- TransformRotation: swap quat Y/Z, W kept (left- to right-handed)
- the root bone node (index 0) additionally conjugated

From a PSA key (x,y,z = pos, X,Y,Z,W = quat):
```
pos_gl  = ( x,  z, -y) * 0.01
quat_gl = ( X,  Z, -Y, -W)             (non-root)
quat_gl = (-X, -Z,  Y, -W)             (root — conjugated)
```
Both translations and rotations are parent-relative, matching the glTF
node local transforms, so channels target the nodes directly. The L2
tracks carry FULL position tracks (bind offsets + animation) — verified
against the glTF rests (UpperArm 2.774 vs 2.77, Calf 11.216 vs 11.22).

## Status

`tools/psa_to_gltf.py` — written and verified (2026-11-15): injects a PSA
sequence as a glTF animation into the character part files.
`Run_Hand_FDarkElf` (16 frames @ 24 fps) lives in all six
`assets/character/FDarkElf_m000_*.gltf`. Idle (Wait_Hand) / walk (Walk_Hand)
are NOT injected yet — pending the user's go.

UModel CLI still refuses glTF animation export ("glTF animation could be
exported from mesh viewer only"); the `-md5` export works and writes
per-sequence .md5anim files (useful as a cross-check, not used by the
pipeline).
