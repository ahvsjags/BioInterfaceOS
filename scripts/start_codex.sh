#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python scripts/validate_execution_pack.py
exec codex exec \
  --sandbox workspace-write \
  --ask-for-approval never \
  "$(cat CODEX_START_PROMPT.md)"
