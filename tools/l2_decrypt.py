#!/usr/bin/env python3
"""Decrypt Lineage 2 client packages (Lineage2VerXXX XOR schemes).

Schemes (from acmi/L2crypt, MIT):
  Ver111: XOR 0xAC
  Ver121: XOR (sum of chars of lowercase filename) & 0xFF
  Ver120: same as 121 without filename? (unused here)
  NO_CRYPT: header absent -> copy as is

Usage:
  python3 l2_decrypt.py SRC DST
"""
import sys
import struct
import os

HEADER_SIZE = 28


def detect(data):
    if len(data) < HEADER_SIZE:
        return 0, 0
    raw = data[:HEADER_SIZE]
    try:
        s = raw.decode("utf-16-le")
    except UnicodeDecodeError:
        return 0, 0
    if len(s) == 14 and s.startswith("Lineage2Ver") and s[11:].isdigit():
        return int(s[11:]), HEADER_SIZE
    return 0, 0


def xor_key_for(version, filename):
    if version == 111:
        return 0xAC
    if version in (121, 120):
        name = os.path.basename(filename).lower()
        k = 0
        for ch in name:
            k += ord(ch)
        return k & 0xFF
    raise ValueError(f"unsupported version {version}")


def decrypt_bytes(data, filename):
    version, hdr = detect(data)
    if version == 0:
        return data, 0
    key = xor_key_for(version, filename)
    body = bytearray(data[hdr:])
    table = bytes(i ^ key for i in range(256))
    body = body.translate(table)
    return bytes(body), version


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, "rb") as f:
        data = f.read()
    out, ver = decrypt_bytes(data, os.path.basename(src))
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(dst, "wb") as f:
        f.write(out)
    if ver:
        magic = struct.unpack("<I", out[:4])[0]
        ok = "OK" if magic == 0x9E2A83C1 else f"BAD MAGIC 0x{magic:08X}"
        print(f"{os.path.basename(src)}: Ver{ver} -> {ok} ({len(out)} bytes)")
    else:
        print(f"{os.path.basename(src)}: no crypt header, copied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
