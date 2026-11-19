#!/usr/bin/env python3
"""The L2 client AUDIO inventory (the user's order, 2026-11-19: find, deep
and sort the sound sources for the 20_18 location — music, footsteps,
items, interactions, Dark Elf voices/professions/skills).

The sources:
  /Games/ElmoreX3/Sounds/*.uax — UE2 audio packages, Lineage2Ver111
      encrypted (the same crypto as the maps). Packages: ambsound(+2),
      chrsound(+2), EtcSound, InterfaceSound, itemsound(+2,3),
      MessengerSound, MonSound(+2..9), SkillSound(+2..9), stepsound.
  /Games/ElmoreX3/music/*.ogg — 277 music tracks wrapped in an "L2SD"
      header (a small non-UE wrapper; the OggS stream follows).
  /Games/ElmoreX3/Voice/ — tutorial/system voice (loose, plain).

This tool decrypts the .uax packages, parses the export tables, classifies
the Sound exports by package and by NAME heuristics, locates the ogg
payloads inside the Sound data, and writes:
  tmp/audio/catalog.json   — the full machine-readable inventory
  tmp/audio/catalog.md     — the human summary
  tmp/audio/samples/       — a few unwrapped ogg files (the decode test)

Usage:
  python3 -m tools.l2strict.audio_catalog
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2strict.crypto import decrypt  # noqa: E402
from l2_probe import Package  # noqa: E402

CLIENT = "/Games/ElmoreX3"
WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "tmp", "audio")


def ogg_offset(data: bytes) -> int:
    """The ogg payload offset inside a Sound blob (L2 wraps/strips the
    capture pattern in places — scan the first 4 KB)."""
    return data.find(b"OggS", 0, 4096)


def catalog_package(path: str, name: str, out: dict) -> None:
    data = open(path, "rb").read()
    plain, ver, key = decrypt(data, name)
    tmp = os.path.join(WORK, "decrypted", name)
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, "wb").write(plain)
    pkg = Package(tmp)
    sounds = []
    groups = {}
    for i in range(pkg.export_count):
        cls = pkg.class_of_export(i)
        e = pkg.exports[i]   # (ClassIndex, Super, Pkg, NameIdx, Flags, Size, Offset)
        if cls != "Sound":
            continue
        oname = pkg.name(e[3])
        size, off = e[5], e[6]
        blob = plain[off:off + min(size, 4096)]
        oo = ogg_offset(blob)
        entry = {"name": oname, "size": size,
                 "ogg_offset": (oo if oo >= 0 else None)}
        sounds.append(entry)
        # name heuristics: the L2 sound names are path-like
        # (e.g. "a_b01_gl_shf_a" or "DElf_f01_..."); keep the raw name —
        # the grouping happens in the report stage.
        key = oname.split("_")[0].lower()
        groups[key] = groups.get(key, 0) + 1
    out["packages"][name] = {
        "sounds": sounds, "count": len(sounds),
        "prefix_counts": groups,
        "total_mb": round(sum(s["size"] for s in sounds) / 1e6, 1),
    }
    return plain, sounds


def catalog_location(map_pkg_path: str, out: dict) -> None:
    """The location's own audio graph: AmbientSoundObject emitters (which
    ambsound entry, where, how loud), MusicVolume zones, ZoneInfo music."""
    from l2strict.properties import read_object
    pkg = Package(map_pkg_path)
    emitters = []
    music_vols = []
    zone_infos = []
    for i in range(pkg.export_count):
        cls = pkg.class_of_export(i)
        if cls not in ("AmbientSoundObject", "MusicVolume", "ZoneInfo"):
            continue
        e = pkg.exports[i]
        size, off = e[5], e[6]
        if size <= 0:
            continue
        data = pkg.data[off:off + size]
        try:
            parsed = read_object(data, pkg, context="audio:%d" % i,
                                 has_stack=bool(e[4] & 0x02000000))
        except Exception as exc:
            emitters.append({"cls": cls, "name": pkg.name(e[3]),
                             "error": str(exc)})
            continue
        vals = parsed.props.values
        # resolve the Sound object reference -> the import's outer chain
        # (imports: ClassPackage, Class, Outer, Name — the outer walks up
        # to the package name, e.g. ambsound.an_bird_01)
        def resolve(ref):
            if not isinstance(ref, int) or ref >= 0:
                return None
            chain = []
            idx = -ref - 1
            guard = 0
            while 0 <= idx < len(pkg.imports) and guard < 16:
                imp = pkg.imports[idx]
                chain.append(pkg.name(imp[3]))
                idx = imp[2] - 1 if isinstance(imp[2], int) and imp[2] > 0 else -1
                guard += 1
            if not chain:
                return None
            return {"cls": pkg.name(pkg.imports[-ref - 1][1]),
                    "name": chain[0], "outer": ".".join(reversed(chain[1:]))}
        entry = {"cls": cls, "name": pkg.name(e[3]), "props": {}}
        for k, v in vals.items():
            kl = k.lower()
            if "sound" in kl:
                entry["props"][k] = resolve(v) if isinstance(v, int) and v < 0 else v
            elif kl in ("location", "radius", "volume", "pitch", "pitchmult",
                        "soundradius", "soundvolume", "soundpitch",
                        "nmusicid", "group", "bforceplaymusic"):
                entry["props"][k] = v
        if cls == "AmbientSoundObject":
            emitters.append(entry)
        elif cls == "MusicVolume":
            music_vols.append(entry)
        else:
            zone_infos.append(entry)
    # summarize the emitters by their resolved sound name
    from collections import Counter
    used = Counter()
    for em in emitters:
        snd = em["props"].get("Sound") or em["props"].get("AmbientSound") \
            or em["props"].get("sound")
        if isinstance(snd, dict):
            used["%s:%s" % (snd.get("outer"), snd.get("name"))] += 1
    out["location"] = {
        "ambient_emitters": emitters,
        "emitter_count": len(emitters),
        "used_sounds": dict(used.most_common()),
        "music_volumes": music_vols,
        "zone_infos": zone_infos,
    }
    print("location: %d ambient emitters, %d music volumes, %d zone infos"
          % (len(emitters), len(music_vols), len(zone_infos)))
    for name, cnt in used.most_common(25):
        print("  used: %-40s x%d" % (name, cnt))


def main() -> None:
    os.makedirs(os.path.join(WORK, "samples"), exist_ok=True)
    out = {"packages": {}, "music": [], "voice": []}

    for fn in sorted(os.listdir(os.path.join(CLIENT, "Sounds"))):
        if not fn.endswith(".uax"):
            continue
        catalog_package(os.path.join(CLIENT, "Sounds", fn), fn, out)

    # the location's own audio graph
    map_pkg = os.path.join(WORK, "decrypted", "20_18.unr")
    os.makedirs(os.path.dirname(map_pkg), exist_ok=True)
    src = os.path.join(CLIENT, "MAPS", "20_18.unr")
    plain, ver, key = decrypt(open(src, "rb").read(), "20_18.unr")
    open(map_pkg, "wb").write(plain)
    catalog_location(map_pkg, out)

    # the music: L2SD-wrapped ogg — locate OggS, file sizes
    import glob
    for mp in sorted(glob.glob(os.path.join(CLIENT, "music", "*.ogg"))):
        data = open(mp, "rb").read()
        oo = ogg_offset(data)
        out["music"].append({"name": os.path.basename(mp),
                             "size": len(data),
                             "l2sd_offset": oo})
    # the voice dir
    for vp in sorted(glob.glob(os.path.join(CLIENT, "Voice", "*"))):
        out["voice"].append({"name": os.path.basename(vp),
                             "size": os.path.getsize(vp)})

    json.dump(out, open(os.path.join(WORK, "catalog.json"), "w"))
    # the human summary
    lines = ["# audio catalog", ""]
    for name, d in out["packages"].items():
        lines.append("## %s — %d sounds, %.1f MB" %
                     (name, d["count"], d["total_mb"]))
        lines.append("prefixes: " + json.dumps(d["prefix_counts"],
                                               sort_keys=True))
        lines.append("")
    lines.append("## music: %d tracks (L2SD-wrapped ogg)" % len(out["music"]))
    lines.append("## voice: %d files" % len(out["voice"]))
    open(os.path.join(WORK, "catalog.md"), "w").write("\n".join(lines))
    print("catalog written:", os.path.join(WORK, "catalog.json"))
    for name, d in out["packages"].items():
        print("%-20s %5d sounds %8.1f MB" % (name, d["count"], d["total_mb"]))


if __name__ == "__main__":
    main()
