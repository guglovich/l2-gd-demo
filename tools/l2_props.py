#!/usr/bin/env python3
"""Lineage 2 (UE2 NC) object property list parser.

Verified on 18_20.unr StaticMeshActor/TerrainSector (Interlude-era client).

Object data layout:
  StateFrame (bit 0x02000000 of export flags):
    node compact, stateNode compact, probeMask 8 bytes, latentAction i32, offset compact
  property list (terminated by name index of "None"):
    name       : compact int (name index)
    info       : u8  -> type = info & 0xF, sizeType = (info>>4)&7, arrayFlag = info>>7
    structName : compact int (if type == STRUCT)
    size       : fixed (1,2,4,12,16) by sizeType 0..4, or u8/u16/i32 for 5/6/7
    arrayIndex : compact int (if arrayFlag and type != BOOL)
    value      : depends on type
Types (L2unreal ordinals):
  0 NONE 1 BYTE 2 INT 3 BOOL 4 FLOAT 5 OBJECT 6 NAME 7 DELEGATE 8 CLASS
  9 ARRAY 10 STRUCT 11 VECTOR 12 ROTATOR 13 STR
"""
import struct

T_NONE, T_BYTE, T_INT, T_BOOL, T_FLOAT, T_OBJECT, T_NAME, T_DELEGATE, \
    T_CLASS, T_ARRAY, T_STRUCT, T_VECTOR, T_ROTATOR, T_STR = range(14)

SIZE_FIXED = {0: 1, 1: 2, 2: 4, 3: 12, 4: 16}


class _R:
    def __init__(self, d, p=0):
        self.d = d
        self.p = p

    def u8(self):
        b = self.d[self.p]
        self.p += 1
        return b

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def compact(self):
        b = self.u8()
        sign = b & 0x80
        r = b & 0x3F
        sh = 6
        if b & 0x40:
            while True:
                b = self.u8()
                r |= (b & 0x7F) << sh
                sh += 7
                if not b & 0x80:
                    break
        return -r if sign else r

    def lstr(self):
        ln = self.compact()
        if ln == 0:
            return ""
        n = ln if ln > 0 else -2 * ln
        raw = self.d[self.p:self.p + n]
        self.p += n
        if ln > 0:
            return raw[:-1].decode("latin-1", "replace")
        return raw[:-2].decode("utf-16-le", "replace")


def _read_value(r, ptype, size, pkg, depth=0, struct_name=None):
    if depth > 8:
        raise ValueError("struct recursion too deep")
    if ptype == T_STRUCT and struct_name in ("Vector", "Rotator", "Color"):
        if struct_name == "Vector":
            val = (r.f32(), r.f32(), r.f32())
        elif struct_name == "Rotator":
            val = (r.i32(), r.i32(), r.i32())
        else:
            val = r.d[r.p:r.p + 4]
        # value reads already advanced r.p by exactly `size` bytes
        return val
    if ptype == T_BYTE:
        return r.u8()
    if ptype == T_INT:
        return r.i32()
    if ptype == T_FLOAT:
        return r.f32()
    if ptype == T_OBJECT:
        return r.compact()
    if ptype == T_NAME:
        return pkg.name(r.compact())
    if ptype == T_VECTOR:
        return (r.f32(), r.f32(), r.f32())
    if ptype == T_ROTATOR:
        return (r.i32(), r.i32(), r.i32())
    if ptype == T_STR:
        return r.lstr()
    if ptype == T_ARRAY:
        cnt = r.compact()
        if cnt < 0 or cnt > 100000 or (cnt > 0 and size > 0 and size // cnt > 65536):
            # implausible count — treat as opaque blob
            r.p += size
            return ("bytes", r.d[r.p - size:r.p])
        end = r.p + size
        # heuristics on element type from data size
        if size == cnt * 2:
            vals = [struct.unpack_from("<h", r.d, r.p + 2 * i)[0] for i in range(cnt)]
            r.p = end
            return vals
        if size == cnt * 4:
            vals = [struct.unpack_from("<i", r.d, r.p + 4 * i)[0] for i in range(cnt)]
            r.p = end
            return vals
        # compact int elements (e.g. arrays of object references)
        try:
            start = r.p
            vals = []
            for _ in range(cnt):
                vals.append(r.compact())
            if r.p != end:
                raise ValueError("compact array size mismatch")
            return vals
        except Exception:
            r.p = start
            raw = r.d[r.p:end]
            r.p = end
            return ("raw", raw)
    if ptype == T_STRUCT:
        # other structs are nested property lists terminated by None
        sub, endpos = read_props(r.d, r.p, pkg, depth + 1)
        r.p = endpos
        return sub
    # NONE / unknown: skip
    raw = r.d[r.p:r.p + size]
    r.p += size
    return ("bytes", raw)


def read_props(data, pos, pkg, depth=0):
    """Read property list starting at pos. Returns (dict, end_pos)."""
    r = _R(data, pos)
    props = {}
    while True:
        name_idx = r.compact()
        if name_idx == 0 or pkg.name(name_idx) == "None":
            return props, r.p
        info = r.u8()
        ptype = info & 0xF
        size_type = (info >> 4) & 7
        arr = info >> 7
        struct_name = None
        if ptype == T_STRUCT:
            struct_name = pkg.name(r.compact())
        if size_type in SIZE_FIXED:
            size = SIZE_FIXED[size_type]
        elif size_type == 5:
            size = r.u8()
        elif size_type == 6:
            size = struct.unpack_from("<H", data, r.p)[0]
            r.p += 2
        else:
            size = r.i32()
        if arr and ptype != T_BOOL:
            array_index = r.compact()
        else:
            array_index = 0
        if ptype == T_BOOL:
            props[pkg.name(name_idx)] = bool(arr)
            continue
        start = r.p
        val = _read_value(r, ptype, size, pkg, depth, struct_name)
        if ptype == T_STRUCT and struct_name not in ("Vector", "Rotator", "Color"):
            # declared size is authoritative; resync even if None came early/late
            r.p = start + size
        nm = pkg.name(name_idx)
        if arr and array_index <= 1024:
            old = props.get(nm)
            if old is None:
                old = []
                props[nm] = old
            elif not isinstance(old, list):
                # first array element was stored without array flag
                old = [old]
                props[nm] = old
            while len(old) <= array_index:
                old.append(None)
            try:
                old[array_index] = val
            except IndexError:
                old.append(val)
        elif not arr:
            props[nm] = val


def read_object(data, pkg, has_stack=None):
    """Read full object: StateFrame (if flagged) + properties. Returns (state, props, end)."""
    r = _R(data)
    if has_stack is None:
        has_stack = bool(r.d[0] if False else True)
    state = None
    if has_stack:
        state = {
            "node": r.compact(),
            "state_node": r.compact(),
            "probe_mask": struct.unpack_from("<q", data, r.p)[0],
        }
        r.p += 8
        state["latent_action"] = r.i32()
        state["offset"] = r.compact()
    props, end = read_props(data, r.p, pkg)
    return state, props, end
