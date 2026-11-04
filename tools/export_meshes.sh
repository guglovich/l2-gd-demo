#!/bin/bash
# Batch export all used village meshes to glTF
ROOT="/home/jinseoyeon/Projects/Lineage 2 Godot"
cd "$ROOT" || exit 1
OUT="$ROOT/tmp/umodel_export"
python3 - <<'EOF' > tmp/export_list.txt
import json
d = json.load(open('tmp/18_20.json'))
pkgs = {}
for a in d['actors']:
    m = a.get('mesh')
    if m and m.get('package'):
        pkgs.setdefault(m['package'], set()).add(m['object'])
for pkg, objs in sorted(pkgs.items()):
    for o in sorted(objs):
        print(f"StaticMeshes/{pkg}.usx {o} StaticMesh")
EOF
N=0
while read -r pkg obj cls; do
  umodel -path="$ROOT/tmp/decrypted" -game=l2 -export -gltf -png -out="$OUT" "$pkg" "$obj" "$cls" >/dev/null 2>>tmp/export_err.log && N=$((N+1)) || echo "FAIL $pkg $obj" >> tmp/export_fail.log
done < tmp/export_list.txt
echo "exported $N meshes"
