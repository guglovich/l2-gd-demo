#!/usr/bin/env bash
# dis <hexva> [len]   raw bytes of engine.dll at a VA
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="$(mktemp -d /tmp/l2scr_XXXXXX)"
"$HERE/gh.sh" "$DIR" R "$@"
rm -rf "$DIR"
