# GitHub Issue #1 — R9.1 independent reproduction and external-user intake

BioInterfaceOS is inviting genuinely non-author teams to evaluate the public `v0.1.3-r9.1` release. This issue is an open request, not a completed receipt.

## Fixed checkout

```bash
git clone --branch v0.1.3-r9.1 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
uv sync --locked --all-groups
uv run pytest -q tests/review_round_3 tests/review_round_4
```

Use the handoff contract at `docs/external/INDEPENDENT_REPRODUCTION_AND_USER_HANDOFF.md`, the evaluator/reproduction protocol at `docs/data/R4_T166_EXTERNAL_EVALUATOR_AND_REPRODUCTION_PROTOCOL.json`, and the adoption intake at `docs/data/R4_T167_EXTERNAL_USER_ADOPTION_INTAKE.json`.

## Current author-run evidence

The R9.1 release contains the T180/T181 route built from the paper-attached PMC7376165 Supplementary Data 5 workbook: 141 biological units, 705 measurement batches, 666 qualified batches, 34 shared canonical proteins and 17,026 external observations. The KAUST author-run receipt records 32 passed tests and valid T180/T181 verifiers. These are same-laboratory exploratory results, not independent validation, a protected lockbox, a no-author reproduction, clinical validation or community adoption.

## What qualifies as external evidence

A qualifying evaluator or reproduction team must be genuinely outside the author project, disclose institution and conflicts, use a clean fixed checkout, reacquire or independently attest all original inputs, record environment/lockfile/container digest, commands, logs and output hashes, report deviations and failures, and submit a signed aggregate receipt at an immutable public locator. Protected row-level inputs and intermediate outputs must remain with the evaluator.

An external user adoption report must identify the institution and task, record installation environment and release tag, include successful and failed tasks, and provide output hashes or an immutable issue/PR/project record. Downloads, stars, page views, author-controlled reruns and Codex agents do not count.

There are currently no verified non-author lockbox receipts, no-author scientific reproduction receipts, external adoption receipts, or archival DOI receipt. Until those real submissions are independently audited, `independent_validation=false`, `external_scientific_reproduction=false`, and `scientific_submission_ready=false` remain in force.
