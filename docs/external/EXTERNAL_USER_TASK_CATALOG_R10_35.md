# External user task catalog — r10.35 handoff

These are two materially different real-data tasks for two distinct
non-author users or institutions. Both require a clean checkout of
`v0.1.3-r10.32`, a real public-data input, environment/dependency hashes,
stdout/stderr and output hashes, failures/limitations, and a signed T218
adoption receipt. Fixtures, author runs, CI and repeated runs by one user do
not count.

## Adoption task A — paper-source audit and paper-attached OOD

Purpose: reacquire and audit the PMC6592156 supplementary route, then run the
paper-attached silver-plasma OOD workflow with fresh output roots.

```bash
uv run biointerfaceos data audit-r3-silver-plasma-source \
  --assets-root data/raw/r3_candidate_pmc6592156 \
  --output-root reports/external_user/adoption_a/source_audit \
  --strict
uv run biointerfaceos data evaluate-r3-silver-external-ood \
  --output-data-root data/raw \
  --feature-root data/raw/r3_uniprot_sequence_features \
  --silver-assets-root data/raw/r3_candidate_pmc6592156 \
  --output-root reports/external_user/adoption_a/ood \
  --strict
```

Required summary: source bytes and hashes, source-cell counts, positive
eligibility, external observations, shared targets, measurement batches,
model/OOD output hashes, and all failed or negative runs.

## Adoption task B — four-source common-target verification

Purpose: independently verify the four-source row-traceable common-target
registry and its explicit technical-batch/donor boundary.

```bash
uv run biointerfaceos data audit-r4-t249-four-lab-common-target \
  --strict
uv run biointerfaceos data verify-r4-t249-four-lab-common-target \
  --strict
```

Required summary: source/laboratory anchor counts, exact common accessions,
row and batch counts, source-map and ledger hashes, license/provenance checks,
unresolved donor units, and any deviations or failures.

The catalog makes adoption easier to perform; it is not evidence of adoption.
Only two distinct non-author users or institutions with independently archived
receipts can close the adoption gate.
