#!/bin/bash
ROOT="/home/jinseoyeon/Projects/Lineage 2 Godot"
cd "$ROOT" || exit 1
for f in tmp/decrypted/Textures/*.utx; do
  name=$(basename "$f" .utx)
  umodel -path="$ROOT/tmp/decrypted" -game=l2 -export -png -out="$ROOT/tmp/umodel_export" "Textures/$name.utx" >/dev/null 2>&1
  echo "done $name"
done
echo ALL_DONE
