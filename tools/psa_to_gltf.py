#!/usr/bin/env python3
"""Convert ActorX PSA animation sequences into glTF animations.

The PSA files come from UModel's ActorX export of L2 MeshAnimation objects
(the CLI refuses glTF animation export: "glTF animation could be exported
from mesh viewer only"). This tool replicates the conversion UModel would
have done, derived from the UEViewer sources (Exporters/ExportPsk.cpp for
the PSA layout, Exporters/ExportGLTF.cpp for the coordinate transform):

VChunkHeader   = name[20] + TypeFlag u32 + DataSize i32 + DataCount i32
FNamedBoneBinary = name[64] + flags u32 + numchildren i32 + parent i32
                   + VJointPosPsk (quat 4f + pos 3f + length 1f + size 3f)
                   = 120 bytes
AnimInfoBinary = name[64] + group[64] + 5 i32 + 3 f32 + 3 i32 = 168 bytes
VQuatAnimKey   = pos 3f + quat 4f (x,y,z,w!) + time 1f = 32 bytes
Keys are FRAME-MAJOR: per sequence, for each frame, all bones.

UModel wrote the keys with MIRROR_MESH enabled (ExportPsk.cpp:21):
    pos.y *= -1; quat.y *= -1; quat.w *= -1      (CQuat = X,Y,Z,W)
Recovering UE values from a PSA key: pos_UE = (x, -y, z); quat_UE = (X, -Y, Z, -W).

UModel's glTF transform (ExportGLTF.cpp):
    TransformPosition: swap Y/Z, scale by 0.01 (UE cm -> glTF m)
    TransformRotation: swap quat Y/Z, keep W (left- to right-handed;
                       "works correctly without" W negation)
    root bone node additionally Conjugate()d.
So from a PSA key:
    pos_gl  = ( x,  z, -y) * 0.01
    quat_gl = ( X,  Z, -Y, -W)            (non-root)
    quat_gl = (-X, -Z,  Y,  W)            (root, conjugated)
  (where x,y,z / X,Y,Z,W are the PSA components)

The animation is injected into existing UModel glTF part files: channels are
emitted only for bone nodes that exist in that glTF (all six FDarkElf parts
carry the full 84-bone skeleton, but the tool does not rely on it).

ROTATION-ONLY (default): the L2 MeshAnimation tracks for the real skeleton
bones (arms, legs, spine) carry NO position keys — the PSA exporter writes
zeros there (DoExportPsa inits BP=(0,0,0) and GetBonePosition leaves it when
the track has no KeyPos). The bind translations come from the glTF node rest
transforms. Emitting the zero translations would collapse the rig. Helper
bones (weapon/shield/skirt/cape dummies) do carry small constant offsets —
their bind offsets are kept from the glTF too. --pos emits the translation
channels anyway (off by default).
Usage:
    python3 -m tools.psa_to_gltf --psa FILE --list
    python3 -m tools.psa_to_gltf --psa FILE --seq Run_Hand_FDarkElf \
        --gltf assets/character/FDarkElf_m000_u.gltf [...]
"""
import argparse
import json
import os
import struct


def read_header(d, o):
    name = d[o:o + 20].split(b"\0")[0].decode()
    ver, size, count = struct.unpack_from("<Iii", d, o + 20)
    return name, ver, size, count, o + 32


def parse_psa(path):
    d = open(path, "rb").read()
    name, ver, size, count, o = read_header(d, 0)
    assert name == "ANIMHEAD", name
    assert ver == 20100422, ver
    name, _, bsize, nbones, o = read_header(d, o)
    assert name == "BONENAMES", name
    bones = [d[o + i * bsize:o + (i + 1) * bsize].split(b"\0")[0].decode()
             for i in range(nbones)]
    o += bsize * nbones
    name, _, isize, nseq, o = read_header(d, o)
    assert name == "ANIMINFO", name
    seqs = []
    for i in range(nseq):
        rec = d[o + i * isize:o + (i + 1) * isize]
        nm = rec[:64].split(b"\0")[0].decode()
        # fields from offset 128: TotalBones, RootInclude, KeyCompressionStyle,
        # KeyQuotum (4 i32), KeyReduction, TrackTime, AnimRate (3 f32),
        # StartBone, FirstRawFrame, NumRawFrames (3 i32)
        totalb, _, _, _ = struct.unpack_from("<4i", rec, 128)
        _, _, rate = struct.unpack_from("<3f", rec, 144)
        _, first, nf = struct.unpack_from("<3i", rec, 156)
        seqs.append({"name": nm, "total_bones": totalb, "rate": rate,
                     "first_frame": first, "num_frames": nf})
    o += isize * nseq
    name, _, ksize, nkeys, o = read_header(d, o)
    assert name == "ANIMKEYS", name
    assert ksize == 32, ksize
    return {"bones": bones, "seqs": seqs, "keys": (d, o, nkeys)}


def key_at(d, base, idx):
    """PSA key -> (pos_gl vec3, quat_gl vec4[x,y,z,w])."""
    px, py, pz = struct.unpack_from("<3f", d, base + idx * 32)
    qx, qy, qz, qw = struct.unpack_from("<4f", d, base + idx * 32 + 12)
    pos = (px * 0.01, pz * 0.01, -py * 0.01)
    quat = (qx, qz, -qy, -qw)
    return pos, quat


def key_at_root(d, base, idx):
    px, py, pz = struct.unpack_from("<3f", d, base + idx * 32)
    qx, qy, qz, qw = struct.unpack_from("<4f", d, base + idx * 32 + 12)
    pos = (px * 0.01, pz * 0.01, -py * 0.01)
    quat = (-qx, -qz, qy, -qw)
    return pos, quat


def inject(gltf_path, seq, bones, keydata, skip=()):
    d, base, _ = keydata
    g = json.load(open(gltf_path))
    if "animations" not in g:
        g["animations"] = []
    if any(a.get("name") == seq["name"] for a in g["animations"]):
        print(f"  {os.path.basename(gltf_path)}: '{seq['name']}' already present, skipped")
        return
    bin_path = os.path.join(os.path.dirname(gltf_path),
                            g["buffers"][0]["uri"])
    bin_data = bytearray(open(bin_path, "rb").read())
    # pad to 4 bytes (alignment for new bufferViews)
    while len(bin_data) % 4:
        bin_data.append(0)
    buf_index = 0

    node_by_name = {}
    for i, n in enumerate(g["nodes"]):
        node_by_name[n.get("name", "")] = i

    fps = seq["rate"]
    nframes = seq["num_frames"]
    times = [i / fps for i in range(nframes)]

    def add_view(data_bytes, count, ctype, ncomp, mn=None, mx=None):
        nonlocal buf_index, bin_data
        g["bufferViews"].append({
            "buffer": buf_index,
            "byteOffset": len(bin_data),
            "byteLength": len(data_bytes),
        })
        bin_data += data_bytes
        acc = {"bufferView": len(g["bufferViews"]) - 1,
               "componentType": ctype, "count": count, "type": ncomp}
        if mn is not None:
            acc["min"], acc["max"] = mn, mx
        g["accessors"].append(acc)
        return len(g["accessors"]) - 1

    # one shared time accessor
    tbytes = struct.pack("<%df" % len(times), *times)
    tacc = add_view(tbytes, len(times), 5126, "SCALAR", mn=[0.0], mx=[times[-1]])

    samplers, channels = [], []
    for bi, bname in enumerate(bones):
        ni = node_by_name.get(bname)
        if ni is None or bname in skip:
            continue
        is_root = bname == bones[0]
        pos, quat = [], []
        for f in range(nframes):
            p, q = (key_at_root if is_root else key_at)(d, base,
                                                        seq["first_frame"] * len(bones) + f * len(bones) + bi)
            pos += p
            quat += q
        pacc = add_view(struct.pack("<%df" % len(pos), *pos), nframes, 5126, "VEC3")
        qacc = add_view(struct.pack("<%df" % len(quat), *quat), nframes, 5126, "VEC4")
        t_sampler = len(samplers)
        samplers.append({"input": tacc, "output": pacc, "interpolation": "LINEAR"})
        r_sampler = len(samplers)
        samplers.append({"input": tacc, "output": qacc, "interpolation": "LINEAR"})
        channels.append({"sampler": t_sampler,
                         "target": {"node": ni, "path": "translation"}})
        channels.append({"sampler": r_sampler,
                         "target": {"node": ni, "path": "rotation"}})

    g["animations"].append({"name": seq["name"],
                            "samplers": samplers, "channels": channels})
    g["buffers"][0]["byteLength"] = len(bin_data)
    open(bin_path, "wb").write(bin_data)
    json.dump(g, open(gltf_path, "w"), indent=1)
    print(f"  {os.path.basename(gltf_path)}: injected '{seq['name']}' "
          f"({len(channels)} rotation channels, {nframes} frames @ {fps}fps)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--psa", required=True)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--seq", default=None)
    ap.add_argument("--skip-bones", default="",
                    help="comma-separated bone names whose channels are NOT "
                    "emitted (e.g. Bip01_head — the L2 run pitch keeps the "
                    "head at the bind orientation, the face stays visible)")
    ap.add_argument("--gltf", nargs="+", default=[])
    args = ap.parse_args()

    psa = parse_psa(args.psa)
    if args.list:
        for s in psa["seqs"]:
            print("%-28s frames=%3d rate=%5.1f first=%d" %
                  (s["name"], s["num_frames"], s["rate"], s["first_frame"]))
        return
    if not args.seq:
        raise SystemExit("--seq required (use --list to see names)")
    seq = next((s for s in psa["seqs"] if s["name"] == args.seq), None)
    if seq is None:
        raise SystemExit(f"sequence '{args.seq}' not found")
    skip = set(x.strip() for x in args.skip_bones.split(",") if x.strip())
    inject_args = (seq, psa["bones"], psa["keys"], skip)
    for g in args.gltf:
        inject(g, *inject_args)


if __name__ == "__main__":
    main()
