#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

TARGET_TRIPLE=$(rustc -vV | sed -n 's/host: //p')
if [ -z "$TARGET_TRIPLE" ]; then
  echo "no se pudo detectar el target triple (¿está rustc en el PATH?)" >&2
  exit 1
fi

PYTHONPATH="../src:." uv run --project .. pyinstaller server.spec --noconfirm

DEST="../src-tauri/binaries/llm-lab-server-${TARGET_TRIPLE}"
mkdir -p ../src-tauri/binaries
cp dist/llm-lab-server "$DEST"
chmod +x "$DEST"

echo "sidecar generado en $DEST"
