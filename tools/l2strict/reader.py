"""Bounds-checked little-endian primitives used by the L2 package parser."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .errors import BoundsError, PropertyError

U8 = struct.Struct("<B")
I8 = struct.Struct("<b")
U16 = struct.Struct("<H")
I16 = struct.Struct("<h")
U32 = struct.Struct("<I")
I32 = struct.Struct("<i")
U64 = struct.Struct("<Q")
I64 = struct.Struct("<q")
F32 = struct.Struct("<f")
F64 = struct.Struct("<d")


@dataclass(slots=True)
class Reader:
    data: bytes
    pos: int = 0
    limit: int | None = None
    context: str = ""

    def __post_init__(self) -> None:
        if self.limit is None:
            self.limit = len(self.data)
        if self.pos < 0 or self.limit < self.pos or self.limit > len(self.data):
            raise BoundsError(
                f"{self.context}: invalid reader window pos={self.pos} "
                f"limit={self.limit} data={len(self.data)}"
            )

    def _need(self, n: int) -> None:
        if n < 0 or self.pos + n > self.limit:
            raise BoundsError(
                f"{self.context}: need {n} byte(s) at 0x{self.pos:X}, "
                f"limit=0x{self.limit:X}"
            )

    def _unpack(self, st: struct.Struct) -> int | float:
        self._need(st.size)
        value = st.unpack_from(self.data, self.pos)[0]
        self.pos += st.size
        return value

    def u8(self) -> int:
        return int(self._unpack(U8))

    def i8(self) -> int:
        return int(self._unpack(I8))

    def u16(self) -> int:
        return int(self._unpack(U16))

    def i16(self) -> int:
        return int(self._unpack(I16))

    def u32(self) -> int:
        return int(self._unpack(U32))

    def i32(self) -> int:
        return int(self._unpack(I32))

    def u64(self) -> int:
        return int(self._unpack(U64))

    def i64(self) -> int:
        return int(self._unpack(I64))

    def f32(self) -> float:
        return float(self._unpack(F32))

    def f64(self) -> float:
        return float(self._unpack(F64))

    def take(self, n: int) -> bytes:
        self._need(n)
        out = self.data[self.pos : self.pos + n]
        self.pos += n
        return out

    def skip(self, n: int) -> None:
        self._need(n)
        self.pos += n

    def compact(self) -> int:
        """Read an Unreal compact int.

        L2 packages use the standard UE2 encoding: bit 7 is the sign of the
        first byte, bit 6 is the first continuation bit, and subsequent bytes
        carry seven data bits each.  A compact int is at most five bytes.
        """
        if self.pos >= self.limit:
            raise BoundsError(f"{self.context}: compact at end of data")
        first = self.data[self.pos]
        self.pos += 1
        negative = bool(first & 0x80)
        value = first & 0x3F
        shift = 6
        if first & 0x40:
            for byte_no in range(4):
                self._need(1)
                byte = self.data[self.pos]
                self.pos += 1
                value |= (byte & 0x7F) << shift
                shift += 7
                if not (byte & 0x80):
                    break
            else:
                raise PropertyError(
                    f"{self.context}: compact int longer than 5 bytes at "
                    f"0x{self.pos - 5:X}"
                )
        return -value if negative else value

    def fstring(self) -> str:
        length = self.compact()
        if length == 0:
            return ""
        if length > 0:
            raw = self.take(length)
            if raw.endswith(b"\x00"):
                raw = raw[:-1]
            return raw.decode("latin-1", "replace")
        raw = self.take((-length) * 2)
        if raw.endswith(b"\x00\x00"):
            raw = raw[:-2]
        return raw.decode("utf-16-le", "replace")

    def remaining(self) -> int:
        return self.limit - self.pos

    def tell(self) -> int:
        return self.pos

    def seek(self, pos: int) -> None:
        if pos < 0 or pos > self.limit:
            raise BoundsError(
                f"{self.context}: seek 0x{pos:X} outside 0..0x{self.limit:X}"
            )
        self.pos = pos
