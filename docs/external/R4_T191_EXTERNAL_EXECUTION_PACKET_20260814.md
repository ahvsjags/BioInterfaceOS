# R4 T191 external execution packet

This packet is the operational handoff for the remaining strong-Q1 gates. It is intentionally a handoff, not a completed external receipt. The current public candidate is the immutable tag v0.1.3-r10.7; resolve its exact commit with git rev-parse v0.1.3-r10.7^{}.

## What an external team may claim

An independent reproduction team may verify the public PXD064962 route from the fixed checkout. A non-author evaluator may run a separate protected-data lockbox only when the evaluator, not the authors, holds the row-level input and intermediate outputs. An external user may submit an adoption report only for a clean installation and a real task.

Author-run commands, Codex agents, fixture data, downloads, stars and page views do not count as any of these gates.

## Reproduction route

~~~text
git clone --branch v0.1.3-r10.7 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
uv sync --locked --all-groups
uv run pytest -q tests/review_round_3 tests/review_round_4
uv run python -m biointerfaceos data verify-r4-pxd064962-source --assets-root data/raw/r4_candidate_pxd064962_ucd --strict
uv run python -m biointerfaceos data evaluate-r4-pxd064962-low-coverage-sensitivity --strict --output-root reports/external_reproduction/t190_low_coverage_sensitivity/v1.0.0
uv run python -m biointerfaceos data verify-r4-pxd064962-low-coverage-sensitivity --strict --output-root reports/external_reproduction/t190_low_coverage_sensitivity/v1.0.0
bash scripts/r4_external_reproduction.sh external_reproduction_run
~~~

The wrapper records the checkout, environment, commands, stdout/stderr and hashes. The team must add its identity, conflict disclosure, source reacquisition log, deviations, failures and signed attestation. The wrapper output is not itself a scientific receipt until the team submits the completed T166/T172 documents.

## Protected lockbox route

The evaluator must independently hold a real held-out input or contribute an unseen real source. The authors must not receive row-level input, intermediate predictions, tuning traces or failure-level results. Before opening the lockbox, the evaluator freezes:

- evaluator identity, institution and conflict disclosure;
- T166 protocol hash and checkout commit;
- protected input manifest or attestation;
- container/environment and dependency-lock hashes;
- primary endpoint, missingness, clustering, uncertainty and negative-control rules.

After one execution, the evaluator submits only aggregate results, complete failure/negative-run records, output hashes, a signed attestation and an immutable archive locator.

## External adoption route

Two non-author teams should each submit the T167 intake with a different clean environment or independent project. Each report must include the task, input provenance, checkout, environment digest, commands, output hashes, successful and failed tasks, limitations and consent for a public summary. An installation without a real task is not adoption.

## Receipt and audit route

Place the three completed documents under one external bundle and run:

~~~text
uv run python -m biointerfaceos data preflight-r4-external-receipts --bundle external_bundle.json --documents-root external_receipts --receipt-out r4_preflight_receipt.json --strict
~~~

The only acceptable structural result is STRUCTURALLY_COMPLETE_PENDING_IDENTITY_REVIEW. The editorial audit must separately verify that the submitters are non-authors, that lockbox custody was independent, that the reproduction began from the fixed checkout, and that the two adoption reports describe real use.

## Current boundary

Until these externally generated artifacts exist and pass identity and checksum review, independent_validation=false, external_scientific_reproduction=false, external_user_adoption=false, doi_archived=false and scientific_submission_ready=false remain mandatory.
