#!/usr/bin/env bash
set -euo pipefail

# Reproduce the public PMC6592156 route from a fixed immutable release.
# This script records evidence only; it never promotes an external claim.

expected_tag="v0.1.3-r10.27"
output_root="${1:-reports/review_round_3/external_reproduction/v1.0.0}"
assets_root="data/raw/r3_candidate_pmc6592156"
feature_root="data/raw/r3_uniprot_sequence_features"
audit_output_root="$output_root/silver_plasma_source_audit"
ood_output_root="$output_root/silver_external_ood"

if [[ "$(git describe --tags --exact-match 2>/dev/null || true)" != "$expected_tag" ]]; then
  echo "This script requires an exact checkout of $expected_tag; moving branches are rejected." >&2
  exit 2
fi

mkdir -p "$output_root"
checkout_commit="$(git rev-parse "${expected_tag}^{}")"
manifest_path="release/empirical_candidate_v0.1.3-r10.27/release_manifest.json"
source_commit="$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["source_commit"])' "$manifest_path")"
manifest_sha256="$(sha256sum "$manifest_path" | awk '{print $1}')"

printf '%s\n' "$expected_tag" > "$output_root/checkout_tag.txt"
printf '%s\n' "$checkout_commit" > "$output_root/checkout_commit.txt"
printf '%s\n' "$source_commit" > "$output_root/source_commit.txt"
printf '%s\n' "$manifest_sha256" > "$output_root/manifest_sha256.txt"
git status --short | tee "$output_root/checkout_status.txt"
python --version 2>&1 | tee "$output_root/python_version.txt"
uv --version 2>&1 | tee "$output_root/uv_version.txt"
uv sync --locked --all-groups 2>&1 | tee "$output_root/environment_install.log"

{
  printf '%s\n' 'uv run pytest -q tests/review_round_3 tests/review_round_4'
  uv run pytest -q tests/review_round_3 tests/review_round_4
} 2>&1 | tee "$output_root/test_run.log"

# The fixed release contains author-run reference reports. Fresh output roots
# keep this no-author run separate and make every newly generated receipt hashable.
{
  printf '%s\n' "uv run biointerfaceos data audit-r3-silver-plasma-source --assets-root $assets_root --output-root $audit_output_root --strict"
  uv run biointerfaceos data audit-r3-silver-plasma-source \
    --assets-root "$assets_root" \
    --output-root "$audit_output_root" \
    --strict
  printf '%s\n' "uv run biointerfaceos data evaluate-r3-silver-external-ood --output-data-root data/raw --feature-root $feature_root --silver-assets-root $assets_root --output-root $ood_output_root --strict"
  uv run biointerfaceos data evaluate-r3-silver-external-ood \
    --output-data-root data/raw \
    --feature-root "$feature_root" \
    --silver-assets-root "$assets_root" \
    --output-root "$ood_output_root" \
    --strict
} 2>&1 | tee "$output_root/reproduction_run.log"

uv lock --check 2>&1 | tee "$output_root/lock_check.log"
sha256sum uv.lock pyproject.toml CITATION.cff > "$output_root/environment_input_hashes.txt"
find "$output_root" -type f ! -name 'output_hashes.txt' -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$output_root/output_hashes.txt"

printf '%s\n' "Run artifacts are in $output_root. Complete the T218 receipt and independent identity/scope audit before making any external claim."
