#!/usr/bin/env python3
"""The baked-mesh 3D-detail pipeline (DEVLOG-90, the user's directive after
the POM pilot was reverted): real displaced geometry in Blender + baked
normal/AO maps, zero UV-shift at runtime.

  L2 mesh (low-poly, UV1 = client tile UVs)
    -> Blender: high-poly = SIMPLE subsurf x3 + Displace by the height
                texture (per material slot), low-poly = the untouched
                import + unique UV2 (Smart UV Project)
    -> bake tangent-space NORMAL + AO through UV2 (Cycles, selected->active)
    -> export the low mesh as glTF (UV1 + UV2) + baked_normal/baked_ao PNGs
    -> the runtime samples the baked maps at UV2 (no swimming, any angle)

Usage:
  python3 tools/l2strict/baked_mesh.py <asset_map_key> [<key>...]
Writes into the staged mesh dir: <Mesh>_baked.gltf/bin + <Mesh>_baked_
normal.png / <Mesh>_baked_ao.png. world.gd picks the *_baked variant up
automatically and switches its material to the baked maps.
"""
import json
import os
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAP_DIR = os.path.join(ROOT, "assets", "maps", "20_18")


# Per-texture height processing (DEVLOG-91). The shaft's natural stone
# reads great with the strong low-pass (blur 12); the PAINTED ornate
# textures need their molding structures preserved — a strong blur erases
# the pilasters/cornices and the base reads as a flat glossy decal
# (the user's verdict). The ornate set: light blur + contrast gamma so the
# bright moldings displace raised and the dark panels recess.
HEIGHT_STYLE = {
    "oren_sylen_001": {"blur": 12, "gamma": 1.0},   # natural stone — keep
    "oren_sylen_in001": {"blur": 5, "gamma": 1.4},  # painted moldings
    "oren_sylen_in002": {"blur": 5, "gamma": 1.4},
    "oren_sylen_in017": {"blur": 5, "gamma": 1.4},
    "oren_sylen_in019": {"blur": 5, "gamma": 1.4},
}
DEFAULT_HEIGHT = {"blur": 12, "gamma": 1.0}


def height_png(albedo_path: str, out_path: str, blur: float, gamma: float) -> None:
    """Grayscale the alpha (height) channel, low-pass filtered to the
    requested scale — the displacement must be driven by the carved SHAPES,
    not the per-texel luminance noise (the DEVLOG-89/90 lesson: noisy
    displacement = spiky high-poly = garbage baked normals = dark
    blotches)."""
    img = Image.open(albedo_path)
    a = np.asarray(img)
    h = Image.fromarray(a[..., 3].astype(np.uint8), "L")
    w, hh = h.size
    h = h.resize((w * 2, hh * 2), Image.BILINEAR).filter(
        ImageFilter.GaussianBlur(blur)).resize((w, hh), Image.BILINEAR)
    h = ImageOps.autocontrast(h, cutoff=(1, 99))
    if gamma != 1.0:
        lut = [int(round(255.0 * ((i / 255.0) ** gamma))) for i in range(256)]
        h = h.point(lut)
    h.save(out_path)


def main() -> None:
    am = json.load(open(os.path.join(MAP_DIR, "asset_map.json")))
    mats = json.load(open(os.path.join(MAP_DIR, "materials.json")))["meshes"]
    work = os.path.join(ROOT, "tmp", "baked_mesh")
    os.makedirs(work, exist_ok=True)

    for key in sys.argv[1:]:
        info = am["meshes"].get(key)
        if info is None:
            raise SystemExit("not in asset_map: %s" % key)
        pkg, obj = key.split(":")
        gltf = os.path.join(ROOT, info["gltf"][len("res://"):])
        texs = mats.get(pkg, {}).get(obj, [])
        pis = info.get("primitive_material_indices", [])
        slot_specs = []
        for si, pi in enumerate(pis):
            if pi < 0 or pi >= len(texs) or texs[pi] is None:
                continue
            tobj = texs[pi]["object"]
            alb = os.path.join(MAP_DIR, "textures", texs[pi]["package"],
                               "Texture", tobj + ".pbr_albedo.png")
            if not os.path.exists(alb):
                alb = os.path.join(MAP_DIR, "textures",
                                   texs[pi]["package"].lower(), "Texture",
                                   tobj + ".pbr_albedo.png")
            hp = os.path.join(work, "%s_S%d_height.png" % (obj, si))
            st = HEIGHT_STYLE.get(tobj, DEFAULT_HEIGHT)
            height_png(alb, hp, st["blur"], st["gamma"])
            # "slot" = the BLENDER slot index (= the surface index si: the
            # glTF importer compacts the used materials 0,1,2,4 into slots
            # 0..3 — keying by the glTF material index dropped the 96-tri
            # ornate base from the dense low, DEVLOG-92)
            slot_specs.append({"slot": si, "height_png": hp,
                               "albedo_png": alb,
                               "displace_m": 0.05,
                               "displace_low_m": 0.0})
        man = {
            "gltf": gltf,
            "out_dir": os.path.join(work, obj),
            "export_name": "%s_baked.gltf" % obj,
            "slots": slot_specs,
            "bake_res": 1024,
        }
        man_path = os.path.join(work, "%s_manifest.json" % obj)
        json.dump(man, open(man_path, "w"))
        bpy_script = os.path.join(ROOT, "tools", "l2strict", "blender_bake.py")
        r = subprocess.run(["blender", "--background", "--python",
                            bpy_script, "--", man_path],
                           capture_output=True, text=True, timeout=600)
        tail = "\n".join((r.stdout + r.stderr).splitlines()[-12:])
        print(tail)
        if "BAKE_DONE" not in r.stdout:
            raise SystemExit("blender bake failed for %s" % key)
        # stage the outputs next to the original glTF
        out_mesh_dir = os.path.dirname(gltf)
        for f in ("%s_baked.gltf" % obj, "%s_baked.bin" % obj,
                  "baked_normal.png", "baked_ao.png", "baked_albedo.png"):
            src = os.path.join(work, obj, f)
            dst = os.path.join(out_mesh_dir,
                               f.replace("baked_normal.png",
                                         "%s_baked_normal.png" % obj)
                               .replace("baked_ao.png",
                                        "%s_baked_ao.png" % obj)
                               .replace("baked_albedo.png",
                                        "%s_baked_albedo.png" % obj))
            shutil.copy(src, dst)
        # WHICH TEXCOORD carries the atlas? The Blender glTF exporter's UV
        # layer order does not match the layer list order (DEVLOG-92: it
        # swapped once). Detect by range: the atlas is 0..1, the client
        # tile UVs exceed 1 (tile units). world.gd reads this sidecar.
        bg = json.load(open(os.path.join(out_mesh_dir,
                                         "%s_baked.gltf" % obj)))
        bb = open(os.path.join(out_mesh_dir, "%s_baked.bin" % obj), "rb").read()
        prim0 = bg["meshes"][0]["primitives"][0]
        ranges = {}
        for k in ("TEXCOORD_0", "TEXCOORD_1"):
            mx = 0.0
            for prim in bg["meshes"][0]["primitives"]:
                acc = bg["accessors"][prim["attributes"][k]]
                bv = bg["bufferViews"][acc["bufferView"]]
                off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                for i in range(acc["count"]):
                    u, v = struct.unpack_from("<2f", bb, off + 8 * i)
                    mx = max(mx, abs(u), abs(v))
            ranges[k] = mx
        # the tile UVs span multiple tiles somewhere in the mesh (>1);
        # the atlas never leaves 0..1
        atlas_in_uv2 = ranges["TEXCOORD_1"] <= 1.01 < ranges["TEXCOORD_0"]
        json.dump({"atlas_in_uv2": bool(atlas_in_uv2)},
                  open(os.path.join(out_mesh_dir, "%s_baked.json" % obj), "w"))
        print("STAGED", key, "->", out_mesh_dir,
              "atlas_in_uv2:", atlas_in_uv2)


if __name__ == "__main__":
    main()
