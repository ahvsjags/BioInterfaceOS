#!/usr/bin/env bash
set -euo pipefail
export BIOINTERFACEOS_NETWORK_DISABLED=1
exec uv run --frozen --offline python -m biointerfaceos reproduce release --strict
