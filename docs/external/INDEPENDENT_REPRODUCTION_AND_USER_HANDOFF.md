# Independent reproduction and external-user handoff

BioInterfaceOS is accepting independent reproduction and external-use reports for the public R8 release. This page is a handoff contract, not a completed receipt.

## Public checkout

```bash
git clone --branch v0.1.3-r9 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
uv sync --locked --all-groups
uv run pytest tests/review_round_3 tests/review_round_4 -q
```

The tag is immutable for this handoff. Do not use the moving `main` branch for a reproduction claim.

## Public author-run replay

The public data replay can verify the released software path and source receipts:

```bash
uv run biointerfaceos data audit-r3-silver-plasma-source --assets-root data/raw/r3_candidate_pmc6592156 --strict
uv run biointerfaceos data evaluate-r3-common-rank-models --output-data-root data/raw --feature-root data/raw/r3_uniprot_sequence_features --strict
uv run biointerfaceos data evaluate-r3-silver-external-ood --output-data-root data/raw --feature-root data/raw/r3_uniprot_sequence_features --silver-assets-root data/raw/r3_candidate_pmc6592156 --strict
```

This public replay is useful for installation and software verification. It is not an independent scientific reproduction because the input data are public and the project team controls the release.

## New author-run biological-cohort evidence (T180/T181)

The immutable R9 release contains a separately frozen paper-attached cohort route. T180 audits the PMC7376165 Supplementary Data 5 matrix at cell level; T181 executes a source-local rank OOD analysis on 141 biological units, 666 qualified NP-corona batches and 17,026 external observations. The result is exploratory and same-laboratory: it is not an independent evaluator receipt, a protected lockbox, a no-author reproduction or clinical validation.

For a reviewer or reproducer who wants to inspect this exact route, use the immutable R9 tag (the exact commit is recorded in the release notes) and supply the paper-attached workbook locally under `data/raw/r4_candidate_pxd017052_nsclc/`. The source registry, protocol, source-cell map and output receipts are:

- `docs/data/R4_T180_PXD017052_NSCLC_SOURCE_REGISTRY.json`;
- `docs/data/R4_T181_PXD017052_NSCLC_BIOLOGICAL_OOD_PROTOCOL.json`;
- `reports/review_round_4/pxd017052_nsclc_source_audit/v1.0.0/`;
- `reports/review_round_4/pxd017052_nsclc_biological_ood/v1.0.0/`.

The exact verification commands are:

```bash
uv run biointerfaceos data verify-r4-pxd017052-nsclc-source \
  --assets-root data/raw/r4_candidate_pxd017052_nsclc --strict
uv run biointerfaceos data verify-r4-pxd017052-nsclc-biological-ood --strict
```

These commands verify the author-generated artifacts; they do not turn an author-run result into independent evidence.

## Independent reproduction

An independent team should:

1. declare its identity, institution, conflicts and scope;
2. start from the tagged checkout and reacquire or independently attest the source accession;
3. record the exact environment, lockfile/container digest, commands, logs and output hashes;
4. report every deviation, failed run, negative result and missing source asset;
5. submit the aggregate receipt without exposing protected row-level data;
6. archive the signed report at an immutable DOI or timestamped public location.

The required fields are defined in `docs/data/R4_T166_EXTERNAL_EVALUATOR_AND_REPRODUCTION_PROTOCOL.json`. An external user who only installs the public package should use `docs/data/R4_T167_EXTERNAL_USER_ADOPTION_INTAKE.json` and report both successful and failed tasks.

## Receipt bundle preflight

The three receipt documents are submitted together with
`docs/data/R4_T172_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`. After replacing
the placeholders with a real non-author submission, run:

```bash
uv run biointerfaceos data preflight-r4-external-receipts \
  --bundle external_bundle.json \
  --documents-root external_receipts \
  --receipt-out r4_preflight_receipt.json \
  --strict
```

`STRUCTURALLY_COMPLETE_PENDING_IDENTITY_REVIEW` is the only successful
preflight status. It confirms checksums, schema, declared safeguards and
aggregate-only fields; it does not authenticate identity, independence,
lockbox custody, external reproduction or user adoption. Those claims remain
false until a separate editorial audit verifies real receipts.

## What will not be counted

Author-controlled reruns, Codex subagents working under project control, GitHub page views, automated downloads, synthetic fixtures, and undocumented manual repairs do not count as independent reproduction or adoption.

Until a real receipt is received and verified, `independent_validation`, `external_scientific_reproduction`, and `scientific_submission_ready` remain false.
