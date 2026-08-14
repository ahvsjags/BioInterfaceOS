#!/usr/bin/env bash
set -euo pipefail

# Current no-author reproduction helper for the immutable scientific candidate.
# Download this helper outside a clean v0.1.3-r10.32 checkout and invoke it
# from that checkout; keeping the helper outside the checkout preserves the
# exact-tag clean-working-tree guard.

expected_tag="v0.1.3-r10.32"
expected_manifest_sha256="d56a070a974675be2e3cff217c437d451eb765719ee95cc9c836abebf40c0c51"
output_root="${1:-reports/external_reproduction/r10_32/v1.0.0}"
assets_root="data/raw/r3_candidate_pmc6592156"
feature_root="data/raw/r3_uniprot_sequence_features"
audit_output_root="$output_root/silver_plasma_source_audit"
ood_output_root="$output_root/silver_external_ood"
helper_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

if [[ "$(git describe --tags --exact-match 2>/dev/null || true)" != "$expected_tag" ]]; then
  echo "This helper requires an exact checkout of $expected_tag; moving branches are rejected." >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "This helper requires a clean scientific checkout; local modifications are rejected." >&2
  exit 2
fi

mkdir -p "$output_root"
checkout_commit="$(git rev-parse "${expected_tag}^{}")"
manifest_path="release/empirical_candidate_v0.1.3-r10.32/release_manifest.json"
source_commit="$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["source_commit"])' "$manifest_path")"
manifest_sha256="$(sha256sum "$manifest_path" | awk '{print $1}')"
if [[ "$manifest_sha256" != "$expected_manifest_sha256" ]]; then
  echo "The scientific release manifest hash does not match the fixed r10.32 candidate." >&2
  exit 2
fi

printf '%s\n' "$expected_tag" > "$output_root/checkout_tag.txt"
printf '%s\n' "$checkout_commit" > "$output_root/checkout_commit.txt"
printf '%s\n' "$source_commit" > "$output_root/source_commit.txt"
printf '%s\n' "$manifest_sha256" > "$output_root/manifest_sha256.txt"
sha256sum "$helper_path" > "$output_root/helper_script_sha256.txt"
git status --short | tee "$output_root/checkout_status.txt"
python --version 2>&1 | tee "$output_root/python_version.txt"
uv --version 2>&1 | tee "$output_root/uv_version.txt"
uv sync --locked --all-groups 2>&1 | tee "$output_root/environment_install.log"

{
  printf '%s\n' 'uv run pytest -q tests/review_round_3 tests/review_round_4'
  uv run pytest -q tests/review_round_3 tests/review_round_4
} 2>&1 | tee "$output_root/test_run.log"

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

printf '%s\n' "Fresh output is ready at $output_root. Submit it with the T218 receipt fields and an independent identity/COI attestation; this helper never promotes a claim."
