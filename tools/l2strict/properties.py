"""Strict UE2 property-list parser.

The important details, learned from the L2 packages and the public
l2mapconv/l2mapper implementations:

* Arrays of structs are serialized as repeated property tags with the array
  bit set and an explicit array index.  The first element is sometimes written
  without the array bit.
* Arrays of bytes/objects are serialized the same way, one tag per element.
* Legacy ``StaticMesh.Materials`` is a single ``T_ARRAY`` tag: a compact element
  count followed by that many property lists, each terminated by ``None``.
* A struct's declared byte size is authoritative.  Binary UE structs
  (Vector/Rotator/Color/...) are read directly; all other structs are nested
  property lists.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

from .errors import L2Error, PropertyError
from .package import Package
from .reader import Reader

T_NONE = 0
T_BYTE = 1
T_INT = 2
T_BOOL = 3
T_FLOAT = 4
T_OBJECT = 5
T_NAME = 6
T_DELEGATE = 7
T_CLASS = 8
T_ARRAY = 9
T_STRUCT = 10
T_VECTOR = 11
T_ROTATOR = 12
T_STR = 13

SIZE_FIXED = {0: 1, 1: 2, 2: 4, 3: 12, 4: 16}

# These are the only structs serialized as binary values by the L2 UE2
# packages we consume.  In particular, Matrix and Plane are *nested property
# lists* here (their declared sizes are much larger than 64 bytes), so they
# must not be treated as raw float arrays.
BINARY_STRUCTS = {
    "Vector": ("3f", 12),
    "Rotator": ("3i", 12),
    "Color": ("4B", 4),
}

MAX_ARRAY_ELEMENTS = 2_000_000


@dataclass(slots=True)
class RawBytes:
    data: bytes

    def to_jsonable(self) -> dict:
        return {
            "$raw": base64.b64encode(self.data).decode("ascii"),
            "length": len(self.data),
        }


@dataclass(slots=True)
class PropertyList:
    values: dict[str, Any]
    array_names: set[str]
    start: int
    end: int
    limit: int
    terminated: bool
    padding: int = 0

    def locate(self, name: str) -> bool:
        return name in self.values


@dataclass(slots=True)
class ObjectProperties:
    state: dict[str, int] | None
    props: PropertyList
    start: int
    end: int
    trailing: int


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, RawBytes):
        return value.to_jsonable()
    if isinstance(value, (bytes, bytearray)):
        return {
            "$raw": base64.b64encode(bytes(value)).decode("ascii"),
            "length": len(value),
        }
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def jsonable_values(values: dict[str, Any]) -> dict[str, Any]:
    return {k: _to_jsonable(v) for k, v in values.items()}


def _read_binary_struct(
    r: Reader, struct_name: str, size: int
) -> tuple[int, int, int] | tuple[float, float, float] | bytes:
    fmt, expected = BINARY_STRUCTS[struct_name]
    if size != expected:
        raise PropertyError(
            f"{r.context}: struct {struct_name} declares {size} bytes, expected "
            f"{expected}"
        )
    if fmt == "3f":
        return (r.f32(), r.f32(), r.f32())
    if fmt == "3i":
        return (r.i32(), r.i32(), r.i32())
    if fmt == "4f":
        return (r.f32(), r.f32(), r.f32(), r.f32())
    if fmt == "16f":
        return tuple(r.f32() for _ in range(16))  # type: ignore[return-value]
    if fmt == "4B":
        return r.take(4)
    raise AssertionError(fmt)  # pragma: no cover


def _decode_array(
    data: bytes,
    value_start: int,
    size: int,
    count: int,
    package: Package,
    context: str,
    depth: int,
) -> tuple[Any, int]:
    end = value_start + size
    if count < 0 or count > MAX_ARRAY_ELEMENTS:
        raise PropertyError(f"{context}: implausible array count {count}")
    if end > len(data):
        raise PropertyError(f"{context}: array extends past data")
    if count == 0:
        return b"", end

    # Byte and word arrays are common for bitsets and map data.
    if size == count:
        return data[value_start:end], end
    if size == count * 2:
        r = Reader(data, value_start, end, context=context + " u16 array")
        return [r.u16() for _ in range(count)], end
    if size == count * 4:
        r = Reader(data, value_start, end, context=context + " i32 array")
        return [r.i32() for _ in range(count)], end

    # Legacy StaticMesh.Materials: count property lists, each None-terminated.
    try:
        r = Reader(data, value_start, end, context=context + " struct array")
        elements = []
        for _ in range(count):
            sub = read_property_list(
                data,
                r.pos,
                package,
                context=context + f" element {len(elements)}",
                depth=depth + 1,
                limit=end,
                require_none=True,
            )
            if sub.end <= r.pos:
                raise PropertyError(f"{context}: empty/non-advancing array element")
            elements.append(sub.values)
            r.pos = sub.end
        if r.pos == end:
            return elements, end
    except L2Error:
        pass

    # Compact-int arrays (e.g. arrays of object references).
    try:
        r = Reader(data, value_start, end, context=context + " compact array")
        elements = [r.compact() for _ in range(count)]
        if r.pos == end:
            return elements, end
    except L2Error:
        pass

    return RawBytes(data[value_start:end]), end


def read_property_list(
    data: bytes,
    pos: int,
    package: Package,
    *,
    context: str,
    depth: int = 0,
    limit: int | None = None,
    require_none: bool = False,
) -> PropertyList:
    if depth > 16:
        raise PropertyError(f"{context}: nested property depth exceeded")
    if limit is None:
        limit = len(data)
    r = Reader(data, pos, limit, context=context)
    values: dict[str, Any] = {}
    array_names: set[str] = set()
    terminated = False

    while r.pos < limit:
        prop_start = r.pos
        name_index = r.compact()
        if name_index == 0:
            terminated = True
            break
        name = package.name(name_index)
        if name == "None":
            terminated = True
            break

        info = r.u8()
        ptype = info & 0x0F
        size_type = (info >> 4) & 0x07
        is_array = bool(info & 0x80)

        struct_name: str | None = None
        if ptype == T_STRUCT:
            struct_name = package.name(r.compact())
        elif ptype == T_NONE:
            raise PropertyError(
                f"{context}: property {name!r} has type NONE at 0x{prop_start:X}"
            )
        elif ptype > T_STR:
            raise PropertyError(
                f"{context}: property {name!r} has unknown type {ptype} at "
                f"0x{prop_start:X}"
            )

        if size_type in SIZE_FIXED:
            size = SIZE_FIXED[size_type]
        elif size_type == 5:
            size = r.u8()
        elif size_type == 6:
            size = r.u16()
        elif size_type == 7:
            size = r.i32()
        else:  # pragma: no cover - 3 bits only
            raise PropertyError(f"{context}: bad size type {size_type}")
        if size < 0:
            raise PropertyError(
                f"{context}: property {name!r} has negative size {size}"
            )

        array_index = 0
        if is_array and ptype != T_BOOL:
            array_index = r.compact()
            if array_index < 0 or array_index > MAX_ARRAY_ELEMENTS:
                raise PropertyError(
                    f"{context}: property {name!r} has invalid array index "
                    f"{array_index}"
                )

        value_start = r.pos
        value_end = value_start + size
        if value_end > limit:
            raise PropertyError(
                f"{context}: property {name!r} value 0x{value_start:X}+0x{size:X} "
                f"exceeds limit 0x{limit:X}"
            )

        if ptype == T_BOOL:
            value: Any = is_array
        elif ptype == T_BYTE:
            value = r.u8()
        elif ptype == T_INT:
            value = r.i32()
        elif ptype == T_FLOAT:
            value = r.f32()
        elif ptype == T_OBJECT:
            value = r.compact()
        elif ptype == T_NAME:
            value = package.name(r.compact())
        elif ptype == T_DELEGATE or ptype == T_CLASS:
            value = RawBytes(r.take(size))
        elif ptype == T_ARRAY:
            count_start = r.pos
            count = r.compact()
            count_bytes = r.pos - count_start
            payload_size = size - count_bytes
            if payload_size < 0:
                raise PropertyError(
                    f"{context}: array {name!r} declares {size} bytes but its "
                    f"count uses {count_bytes}"
                )
            value, _ = _decode_array(
                data,
                r.pos,
                payload_size,
                count,
                package,
                f"{context}:{name}",
                depth,
            )
            r.seek(value_end)
        elif ptype == T_STRUCT:
            assert struct_name is not None
            if struct_name in BINARY_STRUCTS:
                value = _read_binary_struct(r, struct_name, size)
            else:
                sub = read_property_list(
                    data,
                    value_start,
                    package,
                    context=f"{context}:{name}<{struct_name}>",
                    depth=depth + 1,
                    limit=value_end,
                    require_none=True,
                )
                if sub.end > value_end:
                    raise PropertyError(
                        f"{context}: struct {name!r} nested data exceeds declared "
                        f"size ({sub.end} > {value_end})"
                    )
                value = sub.values
                r.seek(value_end)
        elif ptype == T_VECTOR:
            value = (r.f32(), r.f32(), r.f32())
        elif ptype == T_ROTATOR:
            value = (r.i32(), r.i32(), r.i32())
        elif ptype == T_STR:
            value = r.fstring()
        else:  # pragma: no cover
            raise PropertyError(f"{context}: unhandled type {ptype}")

        if ptype != T_ARRAY and r.pos != value_end:
            raise PropertyError(
                f"{context}: property {name!r} type {ptype} consumed "
                f"{r.pos - value_start} byte(s), declared {size} "
                f"(tag at 0x{prop_start:X})"
            )
        if ptype == T_ARRAY:
            r.seek(value_end)

        if is_array and ptype != T_BOOL:
            array_names.add(name)
            if name not in values:
                values[name] = []
            elif not isinstance(values[name], list):
                values[name] = [values[name]]
            array = values[name]
            while len(array) <= array_index:
                array.append(None)
            array[array_index] = value
        else:
            if isinstance(values.get(name), list):
                # A scalar first element can be followed by array elements.
                values[name][0] = value
            else:
                values[name] = value

    if require_none and not terminated:
        raise PropertyError(
            f"{context}: property list ended at limit 0x{limit:X} without None"
        )
    return PropertyList(
        values=values,
        array_names=array_names,
        start=pos,
        end=r.pos,
        limit=limit,
        terminated=terminated,
        padding=max(0, limit - r.pos) if terminated else 0,
    )


def read_object(
    data: bytes,
    package: Package,
    *,
    context: str,
    has_stack: bool,
    allow_missing_none: bool = False,
) -> ObjectProperties:
    r = Reader(data, 0, context=context)
    state: dict[str, int] | None = None
    if has_stack:
        state = {
            "node": r.compact(),
            "state_node": r.compact(),
            "probe_mask": r.i64(),
            "latent_action": r.i32(),
            "offset": r.compact(),
        }
    props = read_property_list(
        data,
        r.pos,
        package,
        context=context,
        require_none=not allow_missing_none,
    )
    return ObjectProperties(
        state=state,
        props=props,
        start=r.pos,
        end=props.end,
        trailing=len(data) - props.end,
    )
