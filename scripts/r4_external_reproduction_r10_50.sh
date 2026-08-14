#!/usr/bin/env bash
set -euo pipefail

# Clean-room runner for a genuinely non-author reproduction candidate.
# The public T250 route is used because its row-level source maps and source
# assets are redistributable under the source-specific CC-BY/CC0 boundaries.
# This script never writes scientific_submission_ready=true and never claims
# to be an external receipt by itself.

repository_url="https://github.com/ahvsjags/BioInterfaceOS.git"
expected_tag="v0.1.3-r10.50"
expected_source_commit="07db8ceef9b785bc3fba0f79f346f9f633645a63"
script_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
script_sha256="$(sha256sum "$script_path" | awk '{print $1}')"
run_root="${1:?Usage: $0 /absolute/path/to/fresh-run-directory}"

if [[ "$run_root" != /* ]]; then
  echo "The run directory must be an absolute path outside the checkout." >&2
  exit 2
fi
if [[ -e "$run_root" ]]; then
  echo "The run directory already exists; choose a fresh path." >&2
  exit 2
fi

mkdir -p "$(dirname "$run_root")"
git clone --branch "$expected_tag" --depth 1 "$repository_url" "$run_root"
cd "$run_root"

checkout_commit="$(git rev-parse HEAD)"
if [[ "$checkout_commit" != "$expected_source_commit" ]]; then
  echo "The cloned checkout does not match the fixed source commit." >&2
  exit 2
fi
exact_tag="$(git describe --tags --exact-match 2>/dev/null || true)"
if [[ "$exact_tag" != "$expected_tag" ]]; then
  echo "The cloned checkout does not match the fixed release tag." >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "The scientific checkout is not clean before execution." >&2
  exit 2
fi

output_root="$run_root/external_run"
mkdir -p "$output_root"
printf '%s\n' "$repository_url" > "$output_root/repository_url.txt"
printf '%s\n' "$expected_tag" > "$output_root/checkout_tag.txt"
printf '%s\n' "$checkout_commit" > "$output_root/checkout_commit.txt"
printf '%s\n' "$script_sha256" > "$output_root/helper_script_sha256.txt"

python --version 2>&1 | tee "$output_root/python_version.txt"
uv --version 2>&1 | tee "$output_root/uv_version.txt"
uv sync --locked --all-groups 2>&1 | tee "$output_root/environment_install.log"

{
  printf '%s\n' 'uv run biointerfaceos data verify-r4-t250-four-lab-common-target --strict'
  uv run biointerfaceos data verify-r4-t250-four-lab-common-target --strict
  printf '%s\n' 'uv run pytest -q tests/review_round_4/test_r4_t250_four_lab_common_target_execution.py'
  uv run pytest -q tests/review_round_4/test_r4_t250_four_lab_common_target_execution.py
} 2>&1 | tee "$output_root/reproduction_run.log"

uv lock --check 2>&1 | tee "$output_root/lock_check.log"
sha256sum uv.lock pyproject.toml CITATION.cff \
  release/empirical_candidate_v0.1.3-r10.50/release_manifest.json \
  reports/review_round_4/three_lab_redistributable_common_target/v1.0.0/r4_t192_three_lab_common_target_ledger.csv \
  reports/review_round_4/t250_four_lab_common_target_execution/v1.0.0/r4_t250_four_lab_execution_report.json \
  > "$output_root/environment_input_hashes.txt"
git status --short > "$output_root/post_run_checkout_status.txt"
cat > "$output_root/external_receipt_submission_note.txt" <<'EOF'
This directory is an execution bundle, not an accepted external receipt.
The reproducing team must add identity, institution, role, conflict disclosure,
signature, deviations, failures/negative runs and an immutable archive locator.
Do not add protected row-level values or intermediate predictions.
EOF

find "$output_root" -type f ! -name 'output_hashes.txt' -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$output_root/output_hashes.txt"

printf '%s\n' "Fresh clean-room candidate complete: $output_root"
