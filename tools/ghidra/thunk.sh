#!/usr/bin/env bash
# thunk <hexva>...   resolve E9 jmp rel32 thunks to their targets
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="$(mktemp -d /tmp/l2scr_XXXXXX)"
"$HERE/gh.sh" "$DIR" Thunks "$@"
rm -rf "$DIR"
