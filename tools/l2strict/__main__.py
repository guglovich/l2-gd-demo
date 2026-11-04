"""Command-line entry point for the strict L2 pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from .errors import L2Error
from .extract import extract_map
from .package import Package
from .pipeline import build_map, build_map_data
from .verify import verify_map


def _cmd_probe(args: argparse.Namespace) -> int:
    package = Package.from_file(args.package)
    print(json.dumps(package.summary(), indent=2))
    if args.classes:
        counts = Counter(
            package.class_name_of_export(i) for i in range(package.export_count)
        )
        for name, count in counts.most_common():
            print(f"{name:32} {count}")
    if args.objects:
        for i in range(package.export_count):
            export = package.exports[i]
            print(
                f"{i:5} {package.class_name_of_export(i):24} "
                f"{package.name(export.object_name)}"
            )
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    expected: dict[str, int] = {}
    for item in args.expect or []:
        name, _, value = item.partition("=")
        if not name or not value.isdigit():
            raise SystemExit(f"invalid --expect value: {item!r}")
        expected[name] = int(value)
    data = extract_map(args.package, expected_counts=expected or None)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fp:
            fp.write(text + "\n")
        print(f"wrote {args.out}")
    else:
        print(text)
    print(json.dumps(data["stats"], indent=2), file=sys.stderr)
    return 0


def _cmd_build_data(args: argparse.Namespace) -> int:
    expected: dict[str, int] = {}
    for item in args.expect or []:
        name, _, value = item.partition("=")
        if not name or not value.isdigit():
            raise SystemExit(f"invalid --expect value: {item!r}")
        expected[name] = int(value)
    result = build_map_data(
        source_root=args.source_root,
        work_dir=args.work_dir,
        map_name=args.map,
        neighbors=tuple(args.neighbor or ()),
        expected_counts=expected or None,
    )
    print(
        f"map: {result['map']['source']['path']}\n"
        f"work: {result['work_dir']}\n"
        f"manifest: {result['manifest']}"
    )
    print(json.dumps(result["map"]["stats"], indent=2))
    print(
        "material packages:",
        ", ".join(sorted(result["materials"]["material_packages"])),
    )
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    expected: dict[str, int] = {}
    for item in args.expect or []:
        name, _, value = item.partition("=")
        if not name or not value.isdigit():
            raise SystemExit(f"invalid --expect value: {item!r}")
        expected[name] = int(value)
    result = build_map(
        source_root=args.source_root,
        work_dir=args.work_dir,
        map_name=args.map,
        neighbors=tuple(args.neighbor or ()),
        expected_counts=expected or None,
        assets_dir=args.assets_dir,
    )
    print(
        f"map: {result['map']['source']['path']}\n"
        f"work: {result['work_dir']}\n"
        f"manifest: {result['manifest']}"
    )
    print(json.dumps(result["map"]["stats"], indent=2))
    print(
        "terrain:",
        json.dumps(
            {
                key: result["terrain"][key]
                for key in (
                    "source_height_size",
                    "height_world_size",
                    "origin_game_xy",
                    "clamped_border_samples",
                    "visible_quad_count",
                    "hole_quad_count",
                )
            },
            indent=2,
        ),
    )
    if "assets" in result:
        print("assets:", json.dumps(result["assets"]["summary"], indent=2))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    result = verify_map(
        work_dir=args.work_dir,
        assets_dir=args.assets_dir,
        map_name=args.map,
    )
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="l2strict")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="print package tables and class counts")
    probe.add_argument("package")
    probe.add_argument("--classes", action="store_true")
    probe.add_argument("--objects", action="store_true")
    probe.set_defaults(func=_cmd_probe)

    extract = sub.add_parser("extract", help="extract a map to strict JSON")
    extract.add_argument("package")
    extract.add_argument("--out")
    extract.add_argument(
        "--expect",
        action="append",
        metavar="CLASS=COUNT",
        help="fail unless the map contains exactly COUNT CLASS exports",
    )
    extract.set_defaults(func=_cmd_extract)

    build_data = sub.add_parser(
        "build-data", help="stage, decrypt, extract, and resolve one map"
    )
    build_data.add_argument("--source-root", required=True)
    build_data.add_argument("--work-dir", required=True)
    build_data.add_argument("--map", required=True)
    build_data.add_argument("--neighbor", action="append", default=[])
    build_data.add_argument(
        "--expect",
        action="append",
        metavar="CLASS=COUNT",
        help="fail unless the map contains exactly COUNT CLASS exports",
    )
    build_data.set_defaults(func=_cmd_build_data)

    build = sub.add_parser(
        "build", help="build data, terrain, and optionally exported assets"
    )
    build.add_argument("--source-root", required=True)
    build.add_argument("--work-dir", required=True)
    build.add_argument("--map", required=True)
    build.add_argument("--neighbor", action="append", default=[])
    build.add_argument("--assets-dir")
    build.add_argument(
        "--expect",
        action="append",
        metavar="CLASS=COUNT",
        help="fail unless the map contains exactly COUNT CLASS exports",
    )
    build.set_defaults(func=_cmd_build)

    verify = sub.add_parser("verify", help="verify exported map data and assets")
    verify.add_argument("--work-dir", required=True)
    verify.add_argument("--assets-dir", required=True)
    verify.add_argument("--map", required=True)
    verify.set_defaults(func=_cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except L2Error as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
