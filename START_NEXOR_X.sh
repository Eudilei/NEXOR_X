#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[[ -d .venv ]] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
[[ -f .env ]] || cp .env.example .env
echo "[NEXOR X] Command Center: http://127.0.0.1:8809"
python -m nexor_x.main
