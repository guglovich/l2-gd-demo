#!/usr/bin/env bash
# sym <substring> [limit]   list engine.dll symbol names containing <substring>
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="$(mktemp -d /tmp/l2scr_XXXXXX)"
"$HERE/gh.sh" "$DIR" FindSym "$@"
rm -rf "$DIR"
