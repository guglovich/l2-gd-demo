#!/usr/bin/env python3
"""Build ground height grid from mesh base positions (lower envelope).

The original heightmap texture could not be reliably anchored to the world
tile, so we derive the ground from the 2603 static meshes themselves:
per 64x64-unit cell take the minimum mesh Z (ground = lower envelope),
fill gaps by nearest-neighbour, then smooth.

Usage: python3 build_ground.py assets/data/map.json assets/data/ground.json
"""
import json
import sys

import numpy as np

GRID = 128          # cells per side
CELL = 256.0        # units per cell
X0, Y0 = -65536.0, 65536.0
SCALE = 0.01        # to meters


def main():
    map_path, out_path = sys.argv[1], sys.argv[2]
    m = json.load(open(map_path))
    grid = np.full((GRID, GRID), np.nan, dtype=np.float64)

    pts = []
    for a in m["actors"]:
        if "error" in a or not a.get("mesh"):
            continue
        l = a["location"]
        col = int((l[0] - X0) / CELL)
        row = int((l[1] - Y0) / CELL)
        if 0 <= col < GRID and 0 <= row < GRID:
            z = l[2]
            cur = grid[row][col]
            if np.isnan(cur) or z < cur:
                grid[row][col] = z
    filled = int(np.sum(~np.isnan(grid)))
    print(f"cells with meshes: {filled}/{GRID*GRID}")

    # fill NaN by iterative neighbour averaging (BFS-like passes)
    for _ in range(600):
        nan = np.isnan(grid)
        if not nan.any():
            break
        shifted = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            g = np.roll(grid, (dr, dc), (0, 1))
            shifted.append(g)
        stack = np.stack(shifted)
        mean = np.nanmean(stack, axis=0)
        grid[nan] = mean[nan]
    grid = np.nan_to_num(grid, nan=np.nanmedian(grid))

    # clip vertical outliers between filled cells (limit slope to 8 m/cell)
    for _ in range(40):
        shifted = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            shifted.append(np.roll(grid, (dr, dc), (0, 1)))
        lo = np.min(shifted, axis=0) - 8.0
        hi = np.max(shifted, axis=0) + 8.0
        grid = np.clip(grid, lo, hi)

    # smooth (3 box passes), keep envelope slightly under meshes
    kernel = np.ones((3, 3)) / 9.0
    padded = np.pad(grid, 1, mode="edge")
    for _ in range(3):
        acc = np.zeros_like(grid)
        for dr in range(3):
            for dc in range(3):
                acc += padded[dr:dr + GRID, dc:dc + GRID] * kernel[dr][dc]
        padded = np.pad(acc, 1, mode="edge")
        grid = acc

    out = {
        "cell": CELL * SCALE,
        "x0": X0 * SCALE,
        "y0": Y0 * SCALE,
        "heights": (grid * SCALE).round(3).tolist(),
    }
    json.dump(out, open(out_path, "w"))
    print("saved", out_path, "z range:", grid.min() * SCALE, grid.max() * SCALE)


if __name__ == "__main__":
    main()
