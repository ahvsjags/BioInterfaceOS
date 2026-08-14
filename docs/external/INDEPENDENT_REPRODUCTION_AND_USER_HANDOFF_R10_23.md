# Independent reproduction and external-user handoff for v0.1.3-r10.23

This page is the current handoff contract for the BioInterfaceOS R4 paper-data candidate. It is not a completed evaluator, scientific-reproduction or adoption receipt.

## Fixed public checkout

Use the immutable tag `v0.1.3-r10.23`, whose exact target commit is recorded in the release manifest and GitHub release. Do not use a moving branch for an external claim.

```bash
git clone --branch v0.1.3-r10.23 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
uv sync --locked --all-groups
uv run pytest tests/review_round_3 tests/review_round_4 -q
```

The T217 statistical amendment is the current paper-data analysis boundary:

- T195 is the sole primary estimand: exact nine-target, leave-one-source-anchor-out, measurement-batch-clustered exploratory contrast;
- T197 is same-lineage source-availability sensitivity;
- T198 is paper-cohort threshold/missingness sensitivity with explicit `AUTHOR_NA` rows and no imputation;
- T203 and T209 are author-run paper-data OOD routes and are not independent external validation;
- measurement-batch counts, reported paper units and paper-anchored clusters are not cross-study biological replication n.

The exact protocol, execution report and KAUST replay receipt are:

- `docs/data/R4_T217_STATISTICAL_AMENDMENT_PROTOCOL.json`;
- `docs/review_round_4/R4_T217_STATISTICAL_AMENDMENT_EXECUTION_20260814.md`;
- `docs/review_round_4/R4_T217_KAUST_FRESH_REPLAY_RECEIPT_20260814.json`.

## Non-author evaluator

The lockbox evaluator must be a non-author who independently holds a protected held-out source or unseen real dataset. The evaluator must retain row-level inputs and submit only aggregate results, an environment digest, commands, output hashes, deviations, failures and a signed identity/COI declaration. The project team must not access the protected rows or intermediate outputs.

Use `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json` and `docs/data/R4_T218_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`. Author-run KAUST, Codex agents, GitHub Actions under project control and public downloads do not satisfy this gate.

## No-author scientific reproduction

The reproducing team must reacquire the public accession independently from the fixed tag, record the dependency lockfile and environment hashes, run the declared accession-to-result route without author assistance, preserve failed and negative results, and submit a signed aggregate receipt with an immutable archive locator.

Use `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json` and `docs/data/R4_T218_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`.

The recommended concrete route is the CC-BY-3.0 PMC6592156 silver-nanoparticle human-plasma source. Reacquire its supplementary files from the Europe PMC supplementary endpoint, place them under `data/raw/r3_candidate_pmc6592156`, verify the source bytes, and run:

```bash
uv run biointerfaceos data audit-r3-silver-plasma-source --assets-root data/raw/r3_candidate_pmc6592156 --strict
uv run biointerfaceos data evaluate-r3-silver-external-ood --output-data-root data/raw --feature-root data/raw/r3_uniprot_sequence_features --silver-assets-root data/raw/r3_candidate_pmc6592156 --strict
```

The historical author-run comparison had 30 measurement batches, 953 external observations and 50 shared canonical proteins. Those values are not acceptance targets: the no-author team must report its own hashes, outputs, failures and deviations.

## External adoption

Two non-author users or institutions must install the fixed release in clean environments and run distinct real tasks. Each receipt must identify the user/institution, COI status, environment digest, task, commands, output hashes and any failure or deviation. Downloads, stars, page views, fixtures and author-controlled reruns are not adoption.

Use `docs/data/R4_T218_EXTERNAL_USER_ADOPTION_INTAKE.json`.

## Current gate state

Until genuine third-party receipts are received and independently audited, the following remain false:

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

GitHub Issue #2 is the public coordination request. A response or issue edit is not evidence that external work occurred.
