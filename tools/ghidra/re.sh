#!/usr/bin/env bash
# re <hexva>...   decompile several engine.dll functions in ONE Ghidra session
#   (the headless project is lock-guarded: parallel calls would fail, so the
#   VAs go through a single DecList run reading a file)
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="$(mktemp -d /tmp/l2scr_XXXXXX)"
LIST="$(mktemp /tmp/l2va_XXXXXX.txt)"
OUT="$(mktemp /tmp/l2re_XXXXXX.cpp)"
for va in "$@"; do printf '%s\n' "$va" >> "$LIST"; done
"$HERE/gh.sh" "$DIR" DecList "$LIST" "$OUT"
if [ -f "$OUT" ]; then
    cat "$OUT"
fi
rm -rf "$DIR" "$LIST" "$OUT"
