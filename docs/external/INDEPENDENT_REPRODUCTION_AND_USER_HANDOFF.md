# Independent reproduction and external-user handoff

BioInterfaceOS is accepting independent reproduction and external-use reports for the public R4 release. This page is a handoff contract, not a completed receipt.

## Public checkout

```bash
git clone --branch v0.1.0-r4 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
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

## Independent reproduction

An independent team should:

1. declare its identity, institution, conflicts and scope;
2. start from the tagged checkout and reacquire or independently attest the source accession;
3. record the exact environment, lockfile/container digest, commands, logs and output hashes;
4. report every deviation, failed run, negative result and missing source asset;
5. submit the aggregate receipt without exposing protected row-level data;
6. archive the signed report at an immutable DOI or timestamped public location.

The required fields are defined in `docs/data/R4_T166_EXTERNAL_EVALUATOR_AND_REPRODUCTION_PROTOCOL.json`. An external user who only installs the public package should use `docs/data/R4_T167_EXTERNAL_USER_ADOPTION_INTAKE.json` and report both successful and failed tasks.

## What will not be counted

Author-controlled reruns, Codex subagents working under project control, GitHub page views, automated downloads, synthetic fixtures, and undocumented manual repairs do not count as independent reproduction or adoption.

Until a real receipt is received and verified, `independent_validation`, `external_scientific_reproduction`, and `scientific_submission_ready` remain false.
