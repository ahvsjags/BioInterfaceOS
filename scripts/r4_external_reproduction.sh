#!/usr/bin/env bash
set -euo pipefail

output_root="${1:-external_reproduction_run}"
analysis_output_root="reports/external_reproduction/t190_low_coverage_sensitivity/v1.0.0"
mkdir -p "$output_root"

git rev-parse HEAD | tee "$output_root/checkout_commit.txt"
git status --short | tee "$output_root/checkout_status.txt"
python --version 2>&1 | tee "$output_root/python_version.txt"
uv --version 2>&1 | tee "$output_root/uv_version.txt"
uv sync --locked --all-groups 2>&1 | tee "$output_root/environment_install.log"

{
  printf '%s\n' 'uv run pytest -q tests/review_round_3 tests/review_round_4'
  uv run pytest -q tests/review_round_3 tests/review_round_4
} 2>&1 | tee "$output_root/test_run.log"

{
  printf '%s\n' 'uv run python -m biointerfaceos data verify-r4-pxd064962-source --assets-root data/raw/r4_candidate_pxd064962_ucd --strict'
  uv run python -m biointerfaceos data verify-r4-pxd064962-source --assets-root data/raw/r4_candidate_pxd064962_ucd --strict
  printf '%s\n' 'uv run python -m biointerfaceos data evaluate-r4-pxd064962-low-coverage-sensitivity --strict --output-root reports/external_reproduction/t190_low_coverage_sensitivity/v1.0.0'
  uv run python -m biointerfaceos data evaluate-r4-pxd064962-low-coverage-sensitivity --strict --output-root reports/external_reproduction/t190_low_coverage_sensitivity/v1.0.0
  printf '%s\n' 'uv run python -m biointerfaceos data verify-r4-pxd064962-low-coverage-sensitivity --strict --output-root reports/external_reproduction/t190_low_coverage_sensitivity/v1.0.0'
  uv run python -m biointerfaceos data verify-r4-pxd064962-low-coverage-sensitivity --strict --output-root reports/external_reproduction/t190_low_coverage_sensitivity/v1.0.0
} 2>&1 | tee "$output_root/receipt_verification.log"

uv lock --check 2>&1 | tee "$output_root/lock_check.log"
sha256sum uv.lock pyproject.toml CITATION.cff > "$output_root/environment_input_hashes.txt"
find "$analysis_output_root" -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$output_root/t190_output_hashes.txt"

printf '%s\n' "Run artifacts are in $output_root. Complete the T166/T167/T172 receipts before making any external claim."
