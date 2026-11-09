#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Headless Ghidra runner for Lineage 2 Godot reverse engineering.
#
#   ./gh.sh <script-dir> <ScriptClass> [args...]
#
# Why this dance exists (learned the hard way, 2026-11-09):
#  * The repo path contains spaces. The headless launcher refuses a project
#    path with spaces and also refuses script dirs whose path has spaces.
#    Therefore the imported program lives in /home/jinseoyeon/ghproj/l2echo.
#  * The OSGi script loader caches COMPILED classes per script dir. Rewriting
#    a .java inside a dir it has already compiled keeps running the OLD class,
#    silently and with plausible output. Deleting osgi/compiled-bundles and
#    osgi/felixcache does NOT reliably fix it.
#  * Reliable rule: a NEW script dir per change of a class. The caller passes
#    a fresh dir (or the shifted copy below); the shared sources under
#    tools/ghidra/scripts/ are then copied in, so they stay the truth.
# ---------------------------------------------------------------------------
set -eu
if [ "$#" -lt 2 ]; then
    echo "usage: $0 <script-dir> <ScriptClass> [args...]" >&2
    exit 2
fi
DIR="$1"; shift
NAME="$1"; shift
copy_to() {
    mkdir -p "$1"
    cp "/home/jinseoyeon/Projects/Lineage 2 Godot/tools/ghidra/scripts/"*.java "$1"/
}
copy_to "$DIR"
/opt/ghidra/support/analyzeHeadless /home/jinseoyeon/ghproj l2echo \
    -process engine.dll -noanalysis \
    -scriptPath "$DIR" \
    -postScript "$NAME.java" "$@" > "/tmp/l2gh.$NAME.out" 2>&1 || true
sed -n "s/^INFO  ${NAME}\.java> //p" "/tmp/l2gh.$NAME.out"
grep -E "SCRIPT ERROR|Caused by" "/tmp/l2gh.$NAME.out" >&2 || true
