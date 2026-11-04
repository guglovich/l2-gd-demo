#!/usr/bin/env python3
"""Extract heightmap (TEXF_G16) from L2 texture object into 16-bit PNG.

Usage: python3 l2_heightmap.py TEXTURE.utx OBJECT_NAME OUT.png
"""
import struct
import sys

import numpy as np
from PIL import Image

from l2_probe import Package


def main():
    path, obj_name, out_png = sys.argv[1], sys.argv[2], sys.argv[3]
    p = Package(path)
    idx = None
    for i in range(p.export_count):
        if p.name(p.exports[i][3]) == obj_name:
            idx = i
            break
    if idx is None:
        raise SystemExit(f"object {obj_name} not found")
    cls, sup, pk, nm, fl, size, off = p.exports[idx]
    d = p.data[off:off + size]
    # G16 heightmap: data ends 14 bytes before object end
    # (i32 u_size, i32 v_size, u8 u_bits, u8 v_bits)
    data_len = size - 14 - 62
    data = d[62:62 + data_len]
    h = np.frombuffer(data, dtype="<u2").reshape(256, 256)
    img = Image.fromarray(h, mode="I;16")
    img.save(out_png)
    print(f"saved {out_png}: 256x256 u16, min={h.min()} max={h.max()}")


if __name__ == "__main__":
    main()
