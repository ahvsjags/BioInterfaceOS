#!/usr/bin/env bash
set -euo pipefail
export BIOINTERFACEOS_NETWORK_DISABLED=1
exec uv run --frozen --offline pytest -q tests/benchmark tests/test_catalog.py tests/test_manifest.py tests/test_lockbox.py
