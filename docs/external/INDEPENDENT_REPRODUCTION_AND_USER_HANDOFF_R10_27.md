# Independent reproduction and external-user handoff for v0.1.3-r10.27

This is the fixed handoff contract for the BioInterfaceOS R4 paper-data candidate. It is not a completed evaluator, scientific-reproduction or adoption receipt.

## Fixed public checkout

Use the immutable tag `v0.1.3-r10.27`. Resolve `git rev-parse 'v0.1.3-r10.27^{}'`, read `source_commit` and the manifest hash from `release/empirical_candidate_v0.1.3-r10.27/release_manifest.json`, and record all three values in the receipt. Do not use a moving branch for an external claim.

```bash
git clone --branch v0.1.3-r10.27 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
git rev-parse 'v0.1.3-r10.27^{}'
sha256sum release/empirical_candidate_v0.1.3-r10.27/release_manifest.json
uv sync --locked --all-groups
uv run pytest tests/review_round_3 tests/review_round_4 -q
```

The one-command route is `bash scripts/r4_external_reproduction.sh`. It rejects moving branches, records the fixed tag/manifest binding, uses fresh output roots, reruns the public source audit, runs the nested external OOD route, hashes outputs and preserves the conservative claim boundary.

The current release includes T222's frozen public full-text/supplementary-data fallback ledger: four routes, four source registries, eight source maps, four output reports and sixteen hash-bound references. T195 remains the primary nine-target leave-one-source-anchor-out exploratory route; T197 is target-availability sensitivity; T198 is threshold/missingness sensitivity; T203/T209 are author-run paper-data OOD. Batch counts and paper-reported units are not cross-study biological n.

## Non-author lockbox evaluator

The evaluator must be a non-author who independently holds a protected held-out source or unseen real dataset. The evaluator retains row-level inputs and submits only aggregate results, environment digest, commands, output hashes, deviations, failures and signed identity/COI declaration. The project team must not access protected rows or intermediate outputs.

Use `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json` and `docs/data/R4_T218_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`. Author-run KAUST, Codex agents, project-controlled GitHub Actions and public downloads do not satisfy this gate.

## No-author scientific reproduction

Independently reacquire the CC-BY-3.0 PMC6592156 silver-nanoparticle human-plasma supplementary data from the Europe PMC endpoint into `data/raw/r3_candidate_pmc6592156`, record source and environment hashes, then run the script or the equivalent commands:

```bash
uv run biointerfaceos data audit-r3-silver-plasma-source \
  --assets-root data/raw/r3_candidate_pmc6592156 \
  --output-root reports/review_round_3/external_reproduction/v1.0.0/silver_plasma_source_audit \
  --strict
uv run biointerfaceos data evaluate-r3-silver-external-ood \
  --output-data-root data/raw \
  --feature-root data/raw/r3_uniprot_sequence_features \
  --silver-assets-root data/raw/r3_candidate_pmc6592156 \
  --output-root reports/review_round_3/external_reproduction/v1.0.0/silver_external_ood \
  --strict
```

Fresh output roots are required because the public release also contains author-run reference receipts. The reproducing team must preserve failed and negative results and submit a signed aggregate receipt with accession, commands, environment digest, output hashes, deviations and an immutable archive locator. Historical author-run counts are comparison metadata only, not acceptance targets.

## External adoption

Two non-author users or institutions must install this fixed release in clean environments and run distinct real tasks. Each receipt must identify the user/institution, COI status, task and input provenance, commands, environment/dependency digest, output hashes, failures and limitations. Downloads, stars, page views, fixtures and author-controlled reruns are not adoption.

## Current gate state

Until genuine third-party receipts and a real archive receipt are independently audited:

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

GitHub Issue #2 is a coordination request, not evidence that external work occurred.
