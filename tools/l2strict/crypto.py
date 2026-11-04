"""Lineage 2 package decryption.

The source client uses a UTF-16LE ``Lineage2VerXXX`` header followed by an
XOR-encrypted UE2 package.  Ver111 uses a fixed key; Ver120/121 derive the key
from the lower-case base filename (including its extension).
"""

from __future__ import annotations

import os
import struct

from .errors import DecryptError

MAGIC = 0x9E2A83C1
HEADER_SIZE = 28


def detect_crypt(data: bytes) -> tuple[int, int]:
    """Return ``(version, header_size)`` or ``(0, 0)`` for plain packages."""
    if len(data) < HEADER_SIZE:
        return 0, 0
    try:
        text = data[:HEADER_SIZE].decode("utf-16-le")
    except UnicodeDecodeError:
        return 0, 0
    if len(text) == 14 and text.startswith("Lineage2Ver") and text[11:].isdigit():
        return int(text[11:]), HEADER_SIZE
    return 0, 0


def key_for(version: int, filename: str) -> int:
    if version == 111:
        return 0xAC
    if version in (120, 121):
        total = sum(ord(ch) for ch in os.path.basename(filename).lower())
        return total & 0xFF
    raise DecryptError(f"unsupported Lineage2Ver{version} encryption")


def decrypt(data: bytes, filename: str) -> tuple[bytes, int, int]:
    """Return ``(plain_data, version, key)``.

    ``version == 0`` means the package had no L2 crypt header and was copied.
    The result is always checked for the UE2 package magic.
    """
    version, header = detect_crypt(data)
    if version == 0:
        if len(data) < 4 or struct.unpack_from("<I", data, 0)[0] != MAGIC:
            raise DecryptError(
                f"{filename}: no Lineage2Ver header and no UE2 package magic"
            )
        return data, 0, 0

    key = key_for(version, filename)
    body = data[header:]
    out = body.translate(bytes(i ^ key for i in range(256)))
    if len(out) < 4:
        raise DecryptError(f"{filename}: decrypted package is too short")
    magic = struct.unpack_from("<I", out, 0)[0]
    if magic != MAGIC:
        raise DecryptError(
            f"{filename}: bad UE2 magic 0x{magic:08X} after Ver{version} decrypt"
        )
    return out, version, key


def decrypt_file(src: str, dst: str) -> dict:
    with open(src, "rb") as fp:
        raw = fp.read()
    plain, version, key = decrypt(raw, os.path.basename(src))
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "wb") as fp:
        fp.write(plain)
    return {
        "source": os.path.abspath(src),
        "output": os.path.abspath(dst),
        "source_size": len(raw),
        "output_size": len(plain),
        "crypt_version": version,
        "xor_key": key,
    }
