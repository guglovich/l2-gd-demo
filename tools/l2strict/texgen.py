#!/usr/bin/env python3
"""Generate the modern PBR texture sets from the CLIENT reference PNGs
(the user's directive 2026-11-13: textures 1:1 with the client, NOT analytic
shaders — the client PNG is the pattern source; we ADD the modern volumetric
layers on top of it):

  <name>.pbr_albedo.png : RGB = the original albedo (1:1), A = height
                          (luminance-derived, blurred — the POM source)
  <name>.pbr_normal.png : RGB = tangent-space normal from the height field,
                          A = roughness (painted-bright = smoother)

Per-texture relief strength lives in RELIEF below (config-only tweaks).
Everything is derived programmatically from the client texture — the layout
and colors are the client's own, so the identity is exact by construction.

Usage:
  python3 tools/l2strict/texgen.py <textures_root> <pkg> <obj> [more...]
e.g.
  python3 tools/l2strict/texgen.py assets/maps/20_18/textures \
      oren_dev_t DE_V_floor01 sylen_temple_t oren_sylen_001_1
"""
import os
import sys

import numpy as np
from PIL import Image

# POM depth (meters of visual depth at texel scale) + normal strength per
# texture. Defaults: floors 0.05 m grooves, carpets flat weave, walls medium.
RELIEF = {
    "DE_V_floor01": (0.055, 2.2),
    "DE_V_floor02": (0.04, 1.8),
    "DE_V_m12": (0.06, 2.0),
    "O_dark_01": (0.05, 1.6),
    "oren_sylen_001_1": (0.05, 2.2),
    "DE_V_capet01": (0.012, 1.0),
    "DE_V_capet02": (0.012, 1.0),
    "DE_V_capet": (0.012, 1.0),
}
DEFAULT_RELIEF = (0.04, 1.6)


def blur(a: np.ndarray, radius: float) -> np.ndarray:
    """ separable gaussian (PIL for speed, normalized back to 0..1) """
    im = Image.fromarray((np.clip(a, 0.0, 1.0) * 255.0).astype(np.uint8), "L")
    im = im.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"])
                   .GaussianBlur(radius))
    return np.asarray(im).astype(np.float32) / 255.0


def sobel_normal(height: np.ndarray, strength: float) -> np.ndarray:
    """tangent-space RGB normal from a height field (signed central diff)"""
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    nx = -gx * strength
    ny = gy * strength          # GL convention: +Y = up in the normal map
    nz = np.ones_like(height)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / ln, ny / ln, nz / ln], axis=-1)
    return (n * 0.5 + 0.5)


def generate(path: str, out_dir: str) -> None:
    obj = os.path.splitext(os.path.basename(path))[0]
    pom, nstrength = RELIEF.get(obj, DEFAULT_RELIEF)
    src = Image.open(path)
    # PRESERVE the source alpha: lattice/grate textures (Iron_net, DE_V_fence)
    # carry a real transparency mask — the cutout holes are part of the
    # material. When the source has a meaningful mask, albedo A = the SOURCE
    # mask (the runtime applies alpha-scissor); otherwise A = the height field.
    has_mask = False
    src_a = None
    if src.mode == "RGBA":
        sa = np.asarray(src)[..., 3].astype(np.float32) / 255.0
        if sa.min() < 0.98:
            has_mask = True
            src_a = sa
    im = src.convert("RGB")
    rgb = np.asarray(im).astype(np.float32) / 255.0
    h, w = rgb.shape[:2]

    lum = rgb.mean(axis=2)
    height = blur(lum, 1.0)
    # height encodes painted relief: bright painted highlights = raised
    height_n = (height - height.min()) / max(1e-6, height.max() - height.min())

    normal = sobel_normal(height, nstrength)

    # roughness: dark painted areas = rougher (0.95), bright = smoother (0.65)
    rough = 0.65 + 0.30 * (1.0 - height_n)

    achan = src_a if has_mask else height_n
    albedo = np.dstack([rgb, achan])
    Image.fromarray((albedo * 255.0).astype(np.uint8), "RGBA").save(
        os.path.join(out_dir, f"{obj}.pbr_albedo.png"))
    nrm = np.dstack([normal, rough])
    Image.fromarray((nrm * 255.0).astype(np.uint8), "RGBA").save(
        os.path.join(out_dir, f"{obj}.pbr_normal.png"))
    # POM depth travels in the material config, not the texture; write a small
    # sidecar json so the runtime reads the tuned values per texture.
    import json
    side = os.path.join(out_dir, f"{obj}.pbr.json")
    json.dump({"pom": pom, "normal_strength": nstrength, "tile": [w, h],
               "alpha_mask": has_mask},
              open(side, "w"))
    print(f"{obj}: {w}x{h} pom={pom} nstrength={nstrength} alpha_mask={has_mask}")


def main() -> None:
    root, args = sys.argv[1], sys.argv[2:]
    pairs = []
    i = 0
    while i < len(args):
        pkg, obj = args[i], args[i + 1]
        i += 2
        # the staged layout: <root>/<pkg>/Texture/<obj>.png (case fallbacks)
        cands = [os.path.join(root, pkg, "Texture", obj + ".png"),
                 os.path.join(root, pkg.lower(), "Texture", obj + ".png")]
        for c in cands:
            if os.path.exists(c):
                pairs.append(c)
                break
        else:
            print("MISSING", pkg, obj)
    for p in pairs:
        generate(p, os.path.dirname(p))


if __name__ == "__main__":
    main()
