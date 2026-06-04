#!/usr/bin/env bash
# Render build: always install from repo root (where requirements.txt lives).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -f requirements.txt ]]; then
  echo "ERROR: requirements.txt not found in ${ROOT}" >&2
  ls -la "$ROOT" >&2
  exit 1
fi

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
