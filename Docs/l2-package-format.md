# L2 / UE2 package format (NC Soft modification)

Reference for reading Lineage 2 client packages (ver 123, licensee 15–28).
All multi-byte integers are little-endian.

## Decryption

First 28 bytes: UTF-16LE string `Lineage2Ver<NNN>` (e.g. `Lineage2Ver111`).
- Ver **111**: rest of file XOR **0xAC**.
- Ver **121**: rest XOR `(sum of chars of lowercase filename) & 0xFF`.
- No header → not encrypted (`.ukx` animations in this client).

After decryption the file starts with `0x9E2A83C1` (UE package tag).

## Summary

```
u32  tag 0x9E2A83C1
u16  file_version (123)
u16  licensee_version (28 for maps, 15–20 for usx/utx)
i32  package_flags
i32  name_count, name_offset
i32  export_count, export_offset
i32  import_count, import_offset
byte guid[16]
```

## Name table (at name_offset)

`name_count` entries:
```
u8   len            // includes NUL; 0xFF → int32 signed length, UTF-16 chars
byte[len]           // NUL-terminated string
u32  flags
```
Name **index 0 is the first entry ("None")** — FName indices point there
directly (no +1 adjustment).

## Compact index

```
b0: bit7 = sign, bit6 = more-bytes, bits5..0 = value low 6 bits
following bytes: bit7 = more, bits6..0 = value (shift 6, 13, 20, ...)
value = negative (r) if sign else r
```

## Import table

Per entry: `ClassPackage compact, ClassName compact, PackageIndex i32,
ObjectName compact`. `PackageIndex` links to outer import (-1-based) or
export (1-based). Package file name for an import = walk outer chain to a
`Core.Package:<file>` import.

## Export table

Per entry:
```
ClassIndex compact    // <0 → import -n-1 defines the class
SuperIndex compact
PackageIndex i32      // outer: 0 = top level
ObjectName compact
ObjectFlags u32       // 0x02000000 = RF_HasStack
SerialSize compact
SerialOffset compact  // only if size > 0
```

## Object data (at serial_offset, length serial_size)

1. **StateFrame** only if export flags bit 0x02000000:
   `node compact, stateNode compact, probeMask i64, latentAction i32,
   offset compact`.
2. **Property list**, terminated by name index of "None":
   ```
   name       compact
   info       u8   type = info & 0xF; sizeType = (info>>4)&7; arrayFlag = info>>7
   structName compact   (only if type == STRUCT(10))
   size       fixed: 1,2,4,12,16 for sizeType 0..4; else u8/u16/i32 (5/6/7)
   arrayIndex compact   (only if arrayFlag && type != BOOL)
   value
   ```
   Types: 0 NONE 1 BYTE 2 INT 3 BOOL 4 FLOAT 5 OBJECT 6 NAME 7 DELEGATE 8 CLASS
   9 ARRAY 10 STRUCT 11 VECTOR 12 ROTATOR 13 STR.
   - BOOL: no data, value = arrayFlag.
   - OBJECT/NAME: compact int.
   - VECTOR: 3×f32; ROTATOR: 3×i32; STR: compact len (neg → UTF-16).
   - STRUCT Vector/Rotator/Color: binary. Other structs: nested property
     list until its own "None". Declared `size` is authoritative for resync.
   - ARRAY: compact count then elements. For refs — compact ints. For
     structs — repeated property entries with arrayIndex (the FIRST element
     of the array is usually written **without** the array flag).
   - BYTE with size==4 in usx/utx material objects: enum name (compact).

## Texture / Material objects (usx/utx, licensee 16–37)

Before properties there is a 4-byte unknown field (`MaterialDeserializer`
unk1). After properties and the trailing None: mips —
```
i32 unknown (=0)
i32 byte_count
byte data[byte_count]
i32 u_size, i32 v_size; u8 u_bits, u8 v_bits
```
Repeated per mip (`count` mips comes first — Texture::deserialize in
l2mapconv). Formats: 0x0A = TEXF_G16 (heightmap, u16 per pixel).
