#!/usr/bin/env python3
"""Generate the 20_18 native-interior-floor coverage mask.

The brush BSP carries two floor families:
  * DE_V_floor02 — the native raised interior floor;
  * DE_V_floor01 — the lower common location floor, which extends under it.

The runtime shader discards floor01 fragments under floor02 so only the native
upper floor is visible. Collision is unchanged. The mask is derived exclusively
from the client brush geometry (no hand-painted/synthetic texture).

Usage:
    python3 tools/l2strict/native_floor_mask.py assets/maps/20_18
"""
from __future__ import annotations

import array
import json
import os
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SIZE = 2048
WORLD_GAME = 32768.0
WORLD_M = WORLD_GAME * 0.01


def read_accessor(gltf: dict, raw: bytes, acc_index: int) -> np.ndarray:
    acc = gltf["accessors"][acc_index]
    bv = gltf["bufferViews"][acc["bufferView"]]
    off = bv.get("byteOffset", 0)
    data = raw[off:off + bv["byteLength"]]
    comp = acc.get("componentType", 5126)
    kind = acc["type"]
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[kind]
    fmt = {5126: "f", 5123: "H", 5125: "I", 5121: "B"}[comp]
    arr = array.array(fmt)
    arr.frombytes(data[:acc["count"] * ncomp * arr.itemsize])
    return np.asarray(arr).reshape(-1, ncomp)


def load_mesh(path: Path):
    gltf = json.loads(path.read_text())
    raw = path.with_suffix(".bin").read_bytes()
    return gltf, raw


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    map_dir = Path(sys.argv[1])
    bsp = json.loads((map_dir / "bsp.json").read_text())
    mask = Image.new("L", (SIZE, SIZE), 255)
    draw = ImageDraw.Draw(mask)
    brushes = 0
    triangles = 0
    for br in bsp.get("brushes", []):
        prims = {
            int(f["prim"])
            for f in br.get("faces", [])
            if f.get("prim") is not None
            and f.get("tex") is not None
            and str(f["tex"][1]) == "DE_V_floor02"
        }
        if not prims:
            continue
        path = map_dir / "meshes_bsp" / f"BSP_{br.get('polys', '')}.gltf"
        if not path.exists():
            continue
        gltf, raw = load_mesh(path)
        loc = np.asarray(br.get("location", [0, 0, 0]), dtype=np.float64) * 0.01
        # staged glTF/world: (UE x, UE z, UE y)
        pos = np.asarray([loc[0], loc[2], loc[1]], dtype=np.float64)
        for si, prim in enumerate(gltf["meshes"][0]["primitives"]):
            if si not in prims:
                continue
            verts = read_accessor(gltf, raw, prim["attributes"]["POSITION"]) + pos
            idx = read_accessor(gltf, raw, prim["indices"]).reshape(-1, 3).astype(int)
            for tri in idx:
                a, b, c = verts[tri]
                n = np.cross(b - a, c - a)
                if abs(float(n[1])) < 0.01:
                    continue
                pts = []
                for v in (a, b, c):
                    x = int(round(v[0] / WORLD_M * SIZE))
                    y = int(round(v[2] / WORLD_M * SIZE))
                    pts.append((x, y))
                draw.polygon(pts, fill=0)
                triangles += 1
        brushes += 1
    out = map_dir / "textures" / "oren_dev_t" / "native_floor_mask.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    mask.save(out)
    arr = np.asarray(mask)
    print(f"native floor mask: {brushes} brushes, {triangles} triangles, "
          f"{int((arr == 0).sum())} black px -> {out}")


if __name__ == "__main__":
    main()
