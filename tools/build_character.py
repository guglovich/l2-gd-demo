#!/usr/bin/env python3
"""Build the unified clean-room character glTF (the modern-port rule).

The L2 client assembles the character from SIX separately-animated skeletal
mesh parts (upper/lower/boots/gloves + the face + the hair tuft) — a 2000s
hack: six skeletons, six animation players, six chances for the parts to
desync (the face "sliding off the head" at every animation, the user's
recurring bug). The native Godot way is ONE skeleton, ONE skin, ONE
animation player and the parts as plain skinned meshes.

This tool merges the UModel-exported part glTFs into a single file:

- the skeleton (the node tree) and the skin come from the FIRST part;
- every other part contributes its mesh (all its primitives/accessors are
  copied into the shared buffer with the offsets shifted) and a skinned
  mesh node referencing the shared skin;
- the joint index order is ASSERTED identical across the parts (UModel
  exports the RefSkeleton order — verified for FDarkElf);
- the animations are copied from the first part as-is (they target the
  shared node tree).

Usage:
    python3 -m tools.build_character --base assets/character/FDarkElf_m000_u.gltf \
        --parts assets/character/FDarkElf_m000_l.gltf [...] \
        --out assets/character/FDarkElf_base.gltf
"""
import argparse
import json
import os
import struct


def load(path):
    g = json.load(open(path))
    bin_path = os.path.join(os.path.dirname(path), g["buffers"][0]["uri"])
    g["_bin"] = bytearray(open(bin_path, "rb").read())
    g["_name"] = os.path.basename(path).rsplit(".", 1)[0]
    return g


def copy_mesh(g, out, mesh_index, buffer_offset, bin_data, bind_bone_joint=None):
    """Copy mesh `mesh_index` (+ its accessors/bufferViews) from g into out.

    Returns the new mesh index in out. The accessor indices inside the mesh
    are remapped; the bufferView byteOffsets are shifted by buffer_offset.
    """
    acc_map = {}
    bv_map = {}
    src = g["meshes"][mesh_index]
    new_prims = []
    for prim in src["primitives"]:
        new_attrs = {}
        for attr, ai in prim["attributes"].items():
            if ai not in acc_map:
                acc = dict(g["accessors"][ai])
                bvi = acc["bufferView"]
                if bvi not in bv_map:
                    bv = dict(g["bufferViews"][bvi])
                    bv["buffer"] = 0
                    bv["byteOffset"] = bv.get("byteOffset", 0) + buffer_offset
                    out["bufferViews"].append(bv)
                    bv_map[bvi] = len(out["bufferViews"]) - 1
                acc["bufferView"] = bv_map[bvi]
                out["accessors"].append(acc)
                acc_map[ai] = len(out["accessors"]) - 1
            new_attrs[attr] = acc_map[ai]
        if bind_bone_joint is not None:
            # re-bind every vertex to one bone: JOINTS_0 = the bone x4,
            # WEIGHTS_0 = (1, 0, 0, 0) in the source's component format
            for attr, values_fn in (("JOINTS_0",
                                     lambda acc0: [bind_bone_joint] * 4),
                                    ("WEIGHTS_0", values_for_weights)):
                acc0 = g["accessors"][prim["attributes"][attr]]
                values = values_fn(acc0)
                while len(bin_data) % 4:
                    bin_data.append(0)
                ct = acc0["componentType"]
                n = acc0["count"]
                fmt = {5126: "f", 5121: "B", 5123: "H", 5125: "I"}[ct]
                blob = b"".join(struct.pack("<" + fmt, v) for v in values) * n
                out["bufferViews"].append({"buffer": 0,
                                           "byteOffset": len(bin_data),
                                           "byteLength": len(blob)})
                bin_data += blob
                out["accessors"].append({"bufferView": len(out["bufferViews"]) - 1,
                                         "componentType": ct,
                                         "count": n,
                                         "type": acc0["type"]})
                new_attrs[attr] = len(out["accessors"]) - 1
        new_prim = {"attributes": new_attrs, "mode": prim.get("mode", 4)}
        if "indices" in prim:
            ii = prim["indices"]
            if ii not in acc_map:
                acc = dict(g["accessors"][ii])
                bvi = acc["bufferView"]
                if bvi not in bv_map:
                    bv = dict(g["bufferViews"][bvi])
                    bv["buffer"] = 0
                    bv["byteOffset"] = bv.get("byteOffset", 0) + buffer_offset
                    out["bufferViews"].append(bv)
                    bv_map[bvi] = len(out["bufferViews"]) - 1
                acc["bufferView"] = bv_map[bvi]
                out["accessors"].append(acc)
                acc_map[ii] = len(out["accessors"]) - 1
            new_prim["indices"] = acc_map[ii]
        if "material" in prim:
            new_prim["material"] = prim["material"]
        new_prims.append(new_prim)
    out["meshes"].append({"name": src.get("name", g["_name"]),
                          "primitives": new_prims})
    return len(out["meshes"]) - 1


def values_for_weights(acc0):
    # normalized UBYTE weights: 1.0 = 255; floats: 1.0
    return [255, 0, 0, 0] if acc0["componentType"] == 5121 else [1.0, 0.0, 0.0, 0.0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="the donor part (skeleton + animations)")
    ap.add_argument("--parts", nargs="+", required=True, help="the other parts to merge")
    ap.add_argument("--bind", default="",
                    help="mesh_name=bone_name pairs: re-bind ALL vertices of "
                    "that mesh to the given bone (weight 1.0). The L2 face "
                    "mesh carries a dummy all-on-root skin (in the client it "
                    "is an attached rigid mesh, not skinned) — it must be "
                    "bound to Bip01_head or it swings with the root")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = load(args.base)
    out = {
        "asset": base.get("asset", {"version": "2.0"}),
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [dict(n) for n in base["nodes"]],
        "meshes": [dict(m) for m in base["meshes"]],
        "skins": [dict(s) for s in base.get("skins", [])],
        "accessors": [dict(a) for a in base["accessors"]],
        "bufferViews": [dict(b) for b in base["bufferViews"]],
        "buffers": [{"uri": os.path.basename(args.out).rsplit(".", 1)[0] + ".bin",
                     "byteLength": 0}],
        "animations": [dict(a) for a in base.get("animations", [])],
        "materials": [dict(m) for m in base.get("materials", [])],
    }
    bind_map = {}
    for pair in args.bind.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            bind_map[k.strip()] = v.strip()
    bin_data = bytearray(base["_bin"])
    scene_nodes = list(out["scenes"][0]["nodes"])
    # the merged part meshes ride the base skin (skin 0)
    for ppath in args.parts:
        part = load(ppath)
        # assert the joint orders match (name-by-node)
        base_names = [base["nodes"][j].get("name") for j in base["skins"][0]["joints"]]
        part_names = [part["nodes"][j].get("name") for j in part["skins"][0]["joints"]]
        assert base_names == part_names, \
            f"{part['_name']}: the skin joint order differs from the base — cannot merge"
        buf_off = len(bin_data)
        bin_data += part["_bin"]
        # pad to 4
        while len(bin_data) % 4:
            bin_data.append(0)
        bind_joint = None
        for mesh_name, bone_name in bind_map.items():
            if part["_name"] == mesh_name:
                bind_joint = base_names.index(bone_name)
        mi = copy_mesh(part, out, 0, buf_off, bin_data, bind_joint)
        out["nodes"].append({"name": part["_name"], "mesh": mi, "skin": 0})
        scene_nodes.append(len(out["nodes"]) - 1)
        print(f"merged {part['_name']}: mesh {mi}, node {len(out['nodes'])-1}, "
              f"verts at buffer {buf_off}")
    out["scenes"][0]["nodes"] = scene_nodes
    out["buffers"][0]["byteLength"] = len(bin_data)
    json.dump(out, open(args.out, "w"), indent=1)
    open(os.path.join(os.path.dirname(args.out),
                      out["buffers"][0]["uri"]), "wb").write(bin_data)
    print(f"wrote {args.out}: {len(out['nodes'])} nodes, {len(out['meshes'])} meshes, "
          f"{len(out['animations'])} animations, {len(bin_data)} bytes")


if __name__ == "__main__":
    main()
