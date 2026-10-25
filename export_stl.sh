#!/usr/bin/env bash
# Export the enclosure halves as STLs into output/, tagged with a version.
# Usage: ./export_stl.sh <version>      e.g. ./export_stl.sh v1.0.0
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "Usage: $0 <version>   (e.g. v1.0.0; letters, digits, '.', '_' and '-' only)" >&2
    exit 1
fi
version=$1

root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
out="$root/output"
mkdir -p "$out"

cd "$root"
THREEMAN_VERSION="$version" THREEMAN_OUT_DIR="$out" freecadcmd scripts/export_stl.py

# freecadcmd exits 0 even when the script raises, so check the result
for part in Base Lid; do
    file="$out/ThreeMan_${version}_${part}.stl"
    if [[ ! -s $file ]]; then
        echo "Export failed: $file was not created" >&2
        exit 1
    fi
    echo "Wrote $file"
done
