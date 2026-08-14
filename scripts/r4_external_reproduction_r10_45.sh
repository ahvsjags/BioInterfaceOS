#!/usr/bin/env bash
set -euo pipefail

# Clean-room runner for a genuinely non-author reproduction.
# Download this script outside the run directory. It clones the immutable
# release into a fresh directory, reacquires the public supplementary bytes,
# and never writes a scientific claim or external gate flag.

repository_url="https://github.com/ahvsjags/BioInterfaceOS.git"
expected_tag="v0.1.3-r10.45"
source_url="https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6592156/supplementaryFiles"
expected_source_sha256="99e472edbb71902f9631e8798fd60b5f1898b1e676affd3fd9376b5302c40008"
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
exact_tag="$(git describe --tags --exact-match 2>/dev/null || true)"
if [[ "$exact_tag" != "$expected_tag" ]]; then
  echo "The cloned checkout does not match the fixed release." >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "The scientific checkout is not clean before reacquisition." >&2
  exit 2
fi

output_root="$run_root/external_run"
assets_root="$run_root/data/raw/r3_candidate_pmc6592156"
source_zip="$assets_root/PMC6592156_supplementary.zip"
source_audit_output="$output_root/silver_source_audit"
ood_output="$output_root/silver_external_ood"
mkdir -p "$output_root" "$assets_root/extracted"

printf '%s\n' "$repository_url" > "$output_root/repository_url.txt"
printf '%s\n' "$expected_tag" > "$output_root/checkout_tag.txt"
printf '%s\n' "$checkout_commit" > "$output_root/checkout_commit.txt"
printf '%s\n' "$script_sha256" > "$output_root/helper_script_sha256.txt"
printf '%s\n' "$source_url" > "$output_root/source_locator.txt"

curl --fail --location --retry 3 --connect-timeout 30 --max-time 300 \
  --output "$source_zip.reacquired" "$source_url"
reacquired_sha256="$(sha256sum "$source_zip.reacquired" | awk '{print $1}')"
printf '%s\n' "$reacquired_sha256" > "$output_root/reacquired_source_sha256.txt"
if [[ "$reacquired_sha256" != "$expected_source_sha256" ]]; then
  echo "The independently reacquired supplementary archive hash differs." >&2
  exit 3
fi
mv "$source_zip.reacquired" "$source_zip"

python - "$source_zip" "$assets_root/extracted" <<'PY'
from pathlib import Path
from sys import argv
from zipfile import ZipFile

archive = Path(argv[1])
destination = Path(argv[2]).resolve()
destination.mkdir(parents=True, exist_ok=True)
wanted = "EN-006-C8EN01054D-s002.xlsx"
with ZipFile(archive) as source:
    matches = [member for member in source.infolist() if Path(member.filename).name == wanted]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one {wanted} member")
    member = matches[0]
    target = (destination / wanted).resolve()
    if target.parent != destination:
        raise SystemExit("archive member escaped extraction root")
    target.write_bytes(source.read(member))
PY

sha256sum "$source_zip" "$assets_root/extracted/EN-006-C8EN01054D-s002.xlsx" \
  > "$output_root/reacquired_asset_hashes.txt"
python --version 2>&1 | tee "$output_root/python_version.txt"
uv --version 2>&1 | tee "$output_root/uv_version.txt"
uv sync --locked --all-groups 2>&1 | tee "$output_root/environment_install.log"

{
  printf '%s\n' 'uv run pytest -q'
  uv run pytest -q
  printf '%s\n' 'uv run biointerfaceos data verify-r4-t249-four-lab-common-target --strict'
  uv run biointerfaceos data verify-r4-t249-four-lab-common-target --strict
  printf '%s\n' 'uv run biointerfaceos data verify-r4-t258-source-unit-endpoint-license --strict'
  uv run biointerfaceos data verify-r4-t258-source-unit-endpoint-license --strict
} 2>&1 | tee "$output_root/checkout_verification.log"

{
  printf '%s\n' "uv run biointerfaceos data audit-r3-silver-plasma-source --assets-root $assets_root --output-root $source_audit_output --strict"
  uv run biointerfaceos data audit-r3-silver-plasma-source \
    --assets-root "$assets_root" \
    --output-root "$source_audit_output" \
    --strict
  printf '%s\n' "uv run biointerfaceos data evaluate-r3-silver-external-ood --output-data-root data/raw --feature-root data/raw/r3_uniprot_sequence_features --silver-assets-root $assets_root --output-root $ood_output --strict"
  uv run biointerfaceos data evaluate-r3-silver-external-ood \
    --output-data-root data/raw \
    --feature-root data/raw/r3_uniprot_sequence_features \
    --silver-assets-root "$assets_root" \
    --output-root "$ood_output" \
    --strict
} 2>&1 | tee "$output_root/reproduction_run.log"

uv lock --check 2>&1 | tee "$output_root/lock_check.log"
sha256sum uv.lock pyproject.toml CITATION.cff > "$output_root/environment_input_hashes.txt"
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

printf '%s\n' "Fresh clean-room run complete: $output_root"
