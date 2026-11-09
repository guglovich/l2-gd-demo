#!/usr/bin/env bash
# decomp <hexva> [outfile]   decompile one engine.dll function to stdout
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
VA="$1"
DIR="$(mktemp -d /tmp/l2scr_XXXXXX)"
"$HERE/gh.sh" "$DIR" Decomp "$VA"
rm -rf "$DIR"
