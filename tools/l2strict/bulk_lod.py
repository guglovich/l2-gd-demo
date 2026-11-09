#!/usr/bin/env python3
"""Positional walker for the L2 UStaticMesh bulk body.

Reads a ``StaticMesh`` export's binary tail (everything after the property
list) field by field and logs the exact byte offset of each field, so that a
wrong assumption about the layout shows up as the position where the walk
derails rather than as a silently wrong mesh.

Usage:

    python3 -m tools.l2strict.bulk_lod <usx> <MeshName>

The walk prints a table of consumed fields. Any field marked ``?!`` is one
the walker could not place confidently; the log then says exactly which byte
offset it stopped at assembly, which is where the next RE shot has to go.
Field sizes and order come from the decompiled bodies recorded in
``Docs/RE_STATICMESH.md``.
"""
import struct
import sys

from .package import Package
from .properties import read_object

MAX_COUNT = 4000000

VERTEX_SIZE = 24
UV_SIZE = 8
LIGHTINFO_SIZE = 0x14
SECTION_SIZE = 0x14
LOD_SIZE = 0x60
COORDS_SIZE = 49
FBOX_SIZE = 24


class LayoutError(ValueError):
    """The walk left the bytes the engine would have read."""


def _compact(data, pos, limit):
    if pos >= limit:
        raise ValueError("compact at end of data")
    first = data[pos]
    pos += 1
    more = first & 0x40
    negative = first & 0x80
    value = first & 0x3F
    shift = 6
    while more:
        if pos >= limit:
            raise ValueError("compact truncated")
        b = data[pos]
        pos += 1
        more = b & 0x80
        value |= (b & 0x7F) << shift
        shift += 7
    if negative:
        value = -value - 1
    return value, pos


class Walk:
    def __init__(self, data, start, end):
        self.data = data
        self.base = start
        self.pos = start
        self.end = end
        self.events = []

    def left(self):
        return self.end - self.pos

    def _log(self, kind, what, value):
        self.events.append((kind, self.pos - self.base, what, value))

    def _need(self, n, what):
        if n < 0:
            raise LayoutError("%s: negative size %d" % (what, n))
        if self.pos + n > self.end:
            raise LayoutError(
                "%s needs %d B at +%d, only %d left"
                % (what, n, self.pos - self.base, self.left()))

    def i32(self, what):
        self._need(4, what)
        value = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        self._log("i32", what, value)
        return value

    def f32(self, what):
        self._need(4, what)
        value = struct.unpack_from("<f", self.data, self.pos)[0]
        self.pos += 4
        self._log("f32", what, "%.4f" % value)
        return value

    def skip(self, n, what):
        self._need(n, what)
        self.pos += n
        self._log("skip", what, "%d B" % n)

    def count(self, what, limit=MAX_COUNT):
        value, self.pos = _compact(self.data, self.pos, self.end)
        self._log("count", what, value)
        if value < 0 or value > limit:
            raise LayoutError(
                "%s count %d outside 0..%d at +%d"
                % (what, value, limit, self.pos - self.base - 1))
        return value

    def box(self, what):
        vals = [self.f32(what + ".v%d" % i) for i in range(6)]
        if not (vals[0] <= vals[3] and vals[1] <= vals[4] and vals[2] <= vals[5]):
            raise LayoutError(
                "%s box min>max at +%d: %s"
                % (what, self.pos - self.base - 24自私 := 0, vals))
        return vals
    def box(self, what):
        vals = [self.f32(what + ".v%d" % i) for i in range(6)]
        if vals[0] > vals[3] or vals[1] > vals[4] or vals[2] > vals[5]:
            raise LayoutError("%s box min>max at +%d: %s"
                              % (what, self.pos - self.base - 24, vals))
        return vals
