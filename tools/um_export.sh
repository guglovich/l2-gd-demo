#!/bin/bash
# Export L2 assets via UModel. Usage: um_export.sh PKG [OBJECT CLASS]
set -u
ROOT="/home/jinseoyeon/Projects/Lineage 2 Godot"
OUT="$ROOT/tmp/umodel_export"
cd "$ROOT" || exit 1
exec umodel -path="$ROOT/tmp/decrypted" -game=l2 -export -gltf -png -out="$OUT" "$@"
