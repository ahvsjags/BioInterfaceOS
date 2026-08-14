# Independent reproduction and external-user handoff for v0.1.3-r10.25

This is the fixed handoff contract for the current BioInterfaceOS R4 paper-data candidate. It is not a completed evaluator, scientific-reproduction or adoption receipt.

## Fixed public checkout

Use the immutable tag `v0.1.3-r10.25`, whose dereferenced release commit is `837be0631d4117ee3a1455de6743b411264a769a`; the manifest's source/provenance commit is `0b4e8e1eb0efe4b0dd690c3b77611309a34e7f6e`. Do not use a moving branch for an external claim.

```bash
git clone --branch v0.1.3-r10.25 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
uv sync --locked --all-groups
uv run pytest tests/review_round_3 tests/review_round_4 -q
```

The current release includes T222's frozen public full-text/supplementary-data fallback ledger: four routes, four source registries, eight source maps, four output reports and sixteen hash-bound references. T195 remains the primary nine-target leave-one-source-anchor-out exploratory route; T197 is target-availability sensitivity; T198 is threshold/missingness sensitivity; T203/T209 are author-run paper-data OOD. Batch counts and paper-reported units are not cross-study biological n.

## Non-author lockbox evaluator

The evaluator must be a non-author who independently holds a protected held-out source or unseen real dataset. The evaluator retains row-level inputs and submits only aggregate results, environment digest, commands, output hashes, deviations, failures and signed identity/COI declaration. The project team must not access protected rows or intermediate outputs.

Use `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json` and `docs/data/R4_T218_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`. Author-run KAUST, Codex agents, project-controlled GitHub Actions and public downloads do not satisfy this gate.

## No-author scientific reproduction

Independently reacquire the CC-BY-3.0 PMC6592156 silver-nanoparticle human-plasma supplementary data from the Europe PMC endpoint, record source and environment hashes, and run:

```bash
uv run biointerfaceos data audit-r3-silver-plasma-source --assets-root data/raw/r3_candidate_pmc6592156 --strict
uv run biointerfaceos data evaluate-r3-silver-external-ood --output-data-root data/raw --feature-root data/raw/r3_uniprot_sequence_features --silver-assets-root data/raw/r3_candidate_pmc6592156 --strict
```

The reproducing team must preserve failed and negative results and submit a signed aggregate receipt with accession, commands, environment digest, output hashes, deviations and an immutable archive locator. Historical author-run counts are comparison metadata only, not acceptance targets.

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
