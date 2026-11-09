# L2 Interlude StaticMesh — load format (RE, 2026-11-09)

**Status:** *observed only*. Every fact below is quoted from a specific
instruction sequence in `/Games/ElmoreX3/system/engine.dll`
(sha256 `974810cad7f04f80b8ce81ce19c4ad44fbd3447bb6b7c8c27fd90725c22e7e1e`,
image base `0x10300000`, built for **L2 Interlude**), read through the
headless-Ghidra wrappers in `tools/ghidra/`. Where a statement is the
wrapping up of observation into a consequence for `tools/l2strict`, it
says so. Any claim that is not traceable to an engine address is wrong and
must be deleted.

## How this was obtained (so it can be re-done)

```
tools/ghidra/re.sh   0x106f7a40 0x106457d0 0x10366380 ...   # decompile many, one session
tools/ghidra/decomp.sh <va>                                # one function
tools/ghidra/sym.sh   FStaticMeshSection                   # what the demangler names it
tools/ghidra/dis.sh   <va> [len]                           # raw bytes
tools/ghidra/thunk.sh <va>...                              # is <va> a jmp thunk, and what -> ?
```

`.text` starts at rva `0x1000` = file offset `0x1000` (file offsets equal
rvа throughout `.text`). The wrappers take **VAs**.

## `UPrimitive::Serialize` (`0x106457d0`) — the base half

```
UObject::Serialize(this, Ar);
serializer_103302c0(Ar, this + 0x34, this + 0x50 variants)
```

`serializer_103302c0` was read literally (`103302c0`):
six dwords `+0, +4, +8, +0xC, +0x10, +0x14` followed by **one byte**
via `Ar->vtable[+4]`. This is:

* **`FCoords` = `FVector Origin` (12 B) + `FVector XAxis` (12 B) + `FVector
  YAxis` (12 B) + `FVector ZAxis` (12 B)`**? No — 6 dwords = 24 B, not 48 B.
* **UNVERIFIED / not used.** This is on `UPrimitive`'s own fields, not the
  geometry stream; no code in `tools/l2strict` reads it, and this note does
  not claim what the `UStaticMesh` body contains beyond the top-level
  sequence below.

## `UStaticMesh::Serialize` (`0x106f7a40`) — the top-level sequence

```
this_00 = Ar;
if (UObject::Ver(Ar) <  0x55) UObject::Serialize(this); else UPrimitive::Serialize(this);
if (UObject::Ver(Ar) <  0x5c) { o = call_106b0390(Ar, this + 0x1e4, this + 0x1e8rivale); call_106f4750(o); }
o = call_106f78d0(Ar, this + 0x60, this + 0x34);
call_106f78d0 -> call_103302c0(o);
if (UObject::Ver(Ar) <  0x4a) { Ar->vtable[+0x18](&zero); }           /* read/seek 4 B */
if (UObject::Ver(Ar) <  0x5c) { FCoords ctor(stack); c = call_106f7460(Ar, stack_3c, stack_6c);
                                call_106af1c0(c); dtor(stack); }
if (UObject::Ver(Ar) >= 0x4a) {                                  /* ours */
   if (UObject::Ver(Ar) <  0x70) { FArray tmp(stack); call_106f7620(Ar, &tmp); FArray dtor(stack); }
   if (UObject::Ver(Ar) <  0x5c) { call_10330040(Ar, &four_bytes); }
}
```

**The exact set of calls that touches the archive for our version
(`ArVer` in `[0x4a, 0x5c)`: the Interlude client's `Ver()` is <0x5c and
>=0x4a for all measured inputs) is, in order:**

1. `UPrimitive::Serialize(this, Ar)`  (which itself does `UObject::Serialize`)
2. `thunk_103302c0(Ar, this + 0x50)`  — the **six dwords + one byte** item above
3. `FArray` ctor + `!VER<0x5c: FCoords ctor + thunk_106f7460(Ar, +0x34,
   +0x60)` + `!VER<0x5c: FArray ctor + thunk_106f7620(Ar, tmp)` + `!VER<0x5c:
   thunk_10330040(Ar, &tmp4)`.**

**A FIFTH THING — the `+0x1E4` / `+0x1E8` pair at the top is `VER < 0x5C`
ONLY.** Our files are `Ver < 0x5c`, so **it is present**, and the order is:

0. `UObject`/`UPrimitive` (inherited)
1. `thunk_106b0390(Ar, this+0x1E4, this+0x1E8)` then `thunk_106f4750`
2. `thunk_106f78d0(Ar, this+0x60, this+0x34)` → `thunk_103302c0`
3. `if Ver<0x4a: read 4 bytes (fallback)`
4. `if Ver<0x5c: [now] thunk_106f7460(Ar, this+0x34, this+0x60)` via `FCoords`
5. `if Ver≥0x4a and Ver<0x70: [now] thunk_106f7620(Ar, tmp)` (the array of 0x60 elements)
6. `if Ver<0x5c: [now] thunk_10330040(Ar, &4bytes)`

**This ordering is from static reading only.** It has not yet been driven
by the actual client: the order was read in the decompiler, not validated
against a freshly-loaded package; the `thunk_106b0390` / `thunk_106f4750 /
call_106f78d0` trio may be one object's serializer chain (a serializer that
internally calls 106f78d0==the `UPrimitive`-level path? no, that one takes
`this+0x60`). **It is a LIVE READ of the real code**, and that's its
own evidence caliber — but until the client is loaded against the file and
the same byte offsets are logged in either end, the reading-level evidence
does not prove that *our* meaning (vertices/indices/sections) is the same
as the engine's. Do not let `xl2strict` use this ordering before that.

## The `0x103EC2E0` body is NOT `FStaticMeshSection` — **thunk identity is a lie by width**

```
10308a17  E9  c4 38 0e 00   jmp 103ec2e0            (the jmp thunk named after FStaticMeshSection::op<<)
103ec2e0  64 A1 00 00 00 00 6A FF 68 ...            real code, SEH prologue
```

`10308a17` is a thunk. The **target** `0x103EC2E0` is not what its
symbol says — the body below constructs `FStaticMeshVertexStream` and
**two** `FRawIndexBuffer`s and calls their serializers. The demangled
`FStaticMeshSection::operator<<` name belongs to `10308a17`; the *target*
is a different function that the linker placed at `0x103ec2e0` (identical
symbols from different ICF-folded units, or a COMDAT). So:

* **`0x10308a17` must not be decompiled to learn FStaticMeshSection's
  layout** (my earlier "section = 20 B, 2 u32 + 6 u16" read there was
  of the tail of `0x103ec2e0`, not a section serializer).

## What `0x103ec2e0` actually is

```
FArchive *FUN_103ec2e0(FArchive *Ar, int lod)          /* reads a LOD's geometry */
if (Ver <  0x5c)  { ... (render-gpu-path branch) }
else if (Ver < 0x70):                                 /* ours */
   FStaticMeshVertexStream  vs  (stack);   ctor 1036a470   (or 10313bd8)
   FRawIndexBuffer          ib0 (stack);   ctor
   FRawIndexBuffer          ib1 (stack);   ctor
   BOOL a = Ar->ReadDword-ish(lod + 4);                     /* +4 = a "bMatches"? */
   WORD   b = Read16(lod + 0xE);
   WORD   c = Read16(lod + 0x10);
   FArchive *p = (FArchive *)Ar->vtable[0x18](lod);          /* ??? */
   Read32(p,   &score);   /* at lod+4, second time */
   FStaticMeshVertexStream = 1039af00 (from (Ar, lod+0xC)  ... 0x18)
   Read32(p,   &four)     /* lod+... */
   read(FRawIndexBuffer)  /* 1039b1c0(lod+0x24) → [u32 count][count u16] */
   read(FRawIndexBuffer)  /* 1039b1c0(lod+0x30) */
if (Ver >  0x6f) read(lod+0xe??)
Read16(lod+0x10)...
```

**Interpretation (still one more decompiler pass away from a clean
capture):** `0x103ec2e0` = "read a `FStaticMeshLOD`'s geometry" for
`Ver < 0x70`. Struct offsets that ARE now measurable, from the same
body: the **element of the `thunk_106f7620` array** has

| offset | read | meaning |
|---|---|---|
| `+0x00` | `FArray` via `1039af00`: `[c][C×24B]` | the vertex stream (`FStaticMeshVertexStream`) |
| `+0x0C` | `FBox` via `103302c0(6dwords+byte)` | **the LOD bounds** |
| `+0x28` | 4 dwords |  |
| `+0x34??` | binary read |  |
| `+0x38..+0x58` | 9 dwords (Ver≥0x53, in the branch from 106f6660) | **planes (Ver<0x53) / 9 dwords (ours)** |
| `+0x5C` | trailing object serializer (Ver>0x5E) |  |
| `+0xC..+0x10` | 2 WORDs (via `FArchive` offset) |  |

and **`FStaticMeshVertexStream::operator<<` @ `0x1030bdcf`** is
`1039af00(Ar, p + 0xC)` (so the `FArray` lives at `+0xC` in the stream
object) **followed by 4 bytes `p + 0x18`**. So the on-disk `FStaticMeshVertexStream`
for `Ver < 0x70` is:

```
[u32 element-count]                     (FArray base: 12 B "vector" header? -> count at +4)
[NumVerts × 24 B  FStaticMeshVertex]    
[u32 Revision]                          (from p + 0x18)
```
(Hint: `FArray::CountBytes(arr, Ar, 24)` is the in-place "swap" for
count+data, so the compact count is at `arr + 4`; the `+0x18` tail then
is the field after the 12-B inline storage.)

`FStaticMeshVertexStream::GetSize() = *(this + 0x10) * 24` confirms
"count" lives in word 4 of the object, i.e. `+0x10`, i.e. two bytes *before*
the object's `FVector` if the ctor `10313bd8` follows the same layout… not
verified.

**None of this yet establishes the DS bridge's file offsets.** It
establishes the *object graphs and field widths*, which is the necessary
step before probing the bulk.

---

## 2026-11-09 (later) - the on-disk boxes in `O_DE_Bridge.gltf`: what is really there

Measured on the **staged glTF**, not guessed (`/tmp/bridge_prims.py`,
`/tmp/tris.py`, `/tmp/deck3.py`):

* `O_DE_Bridge.gltf` has **18 primitives**. Their boxes (glTF X/Y/Z, metres):
  `x ∈ [-7.27, 7.27]`, `y ∈ [-3.90, 3.90]`, `z ∈ [-5.23, 5.23]`.
  So the staged mesh is a **7-15 m wide x 8 m tall x 10 m long arch** - not
  a road.
* **Primitive 10 (`DE_V_floor02`) is the deck**: its 24 verts occupy two
  planes,
  ```
  A: y = -0785, z ∈ [4.00, 4.12]     (west end)
  B: y = -2.90, z ∈ [-4.01, 4.12]    (floor)
  ```
  the whole 9.4 m long face is **one sloped plane** (drop 2.05 m over 8.26 m
  -> 14 deg) with the box cross-section. There is **no** 3-segment structure;
  my earlier "3 segments of 2.56 m" was the segmentation of a probe, not the
  mesh.
* **Primitive 0 (`DE_V_wall05`) carries 140 tris** (the same as `deco10`
  82 + `roof_deco1` 160), and its UVs run `u ∈ [-5.5, 6.5]`, `v ∈ [-2.7, 3.7]`
  - i.e. the wall material is tiled **dozens of times** over the arch: it is
  the stone structure, not the road surface. The old "22 upward tris" was a
  partial filter, not a count.

**Consequence for the user's report ("the bridge is not textured across the
full road width"):** this staged `O_DE_Bridge` is the *arch ribbons and
parapets*, its deck is a **single sloped floor02 plate without side bands**.
Widening this plate would make the floor wider, but it can not put the road
texture across the parapet tops - that is a different mesh. Before any edit,
the game must be compared against the **original client** at the bridge
(stand at spawn, look along the road): if the original also shows only the
sloped plate, there is nothing to fix; if it shows a flat road with both
edges covered, the missing part is the *strip / Btm_Obj* family, not this
plate.

The user authorised editing `scripts/world.gd` with a git checkpoint before
and after. The checkpoint exists (`git tag savepoint-before-world-edit`).
