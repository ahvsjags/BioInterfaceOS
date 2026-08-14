# BioInterfaceOS external evidence handoff — v0.1.3-r10.45

This is an execution handoff, not an external receipt. The current scientific
candidate is a paper-derived computational benchmark/resource. Author-run
analyses, Codex runs, KAUST runs, CI runs, downloads, stars and issue comments
do not satisfy the external gates.

## Immutable candidate

```text
repository=https://github.com/ahvsjags/BioInterfaceOS.git
tag=v0.1.3-r10.45
tag_target=read back the dereferenced immutable tag before running
receipt_preflight_tooling=v0.1.3-r10.46
T238_protocol_sha256=a89a2cf4236caee0826fddde5ac89747f939dd656636d600595adf9af6bed7ea
T249_protocol_sha256=53d9aa48c78f3140b8870bb9469b9264f63bd125beb2a9be4c504bef2e341b63
T258_protocol_sha256=200be8bb0312a155174d7430024644acadf445ae17edc83ebe16d7925ec449b6
```

The source-local rank endpoint is portable only after within-source ranking.
The project does not claim four independent biological cohorts: technical
replicates, pooled/unspecified plasma and patient/timepoint units are recorded
with their actual semantics.

## No-author reproduction

Download `scripts/r4_external_reproduction_r10_45.sh` outside the run
directory and execute it with a new absolute output path:

```bash
bash scripts/r4_external_reproduction_r10_45.sh /tmp/biointerfaceos-r10-45-participant-001
```

The helper clones the immutable tag, independently reacquires the public
PMC6592156 supplementary archive, verifies the expected SHA-256, extracts only
the declared LFQ workbook, installs the locked environment, verifies T249/T258,
runs the source audit and paper-attached OOD, and records commands, logs,
failures, deviations and output hashes. It never sets an external gate.

The participant must submit a signed receipt with identity, institution, role,
conflict disclosure, fixed tag/commit, source URL and hash, environment digest,
commands, output hashes, complete failure/negative-run ledger and an immutable
archive locator.

## Two distinct external adoption tasks

The tasks must be performed by two different non-author users or institutions
in clean environments and must produce separate signed receipts.

### Task A — paper-source audit and OOD

Run the clean-room helper above. Report the independently reacquired source
hash, source-cell counts, 30 condition batches, external OOD observations,
model/ablation/negative-control outputs and all failures.

### Task B — four-source provenance and endpoint audit

From a clean checkout of the same tag, run:

```bash
uv sync --locked --all-groups
uv run biointerfaceos data verify-r4-t249-four-lab-common-target --strict
uv run biointerfaceos data verify-r4-t258-source-unit-endpoint-license --strict
```

Report the exact seven-target intersection, four source anchors, unit semantics,
pairwise endpoint matrix, license/source locators, command logs and hashes.

These are materially different real-data tasks. A catalog or successful command
is not adoption evidence until an external person or institution submits a
signed, hash-bound receipt.

## Non-author protected lockbox

One evaluator must hold protected held-out input or an unseen real dataset under
their control. Authors must not see row-level input, row-level predictions,
intermediate states, tuning traces or failure-level results before the signed
aggregate receipt is finalized. The receipt must include:

- primary estimand and cluster-aware interval;
- effective n by target, measurement cluster and source lineage;
- full versus composition-only paired ablation;
- within-batch rank-permutation negative control;
- all model/OOD summaries and uncertainty intervals;
- complete failure and negative-result ledger;
- identity, institution, role, conflict disclosure, environment digest,
  commands, output hashes, signature and immutable archive locator.

Do not upload protected row-level data or credentials to the repository.

## DOI/archive gate

An authenticated archive must return an immutable locator tied to the fixed
release, and its read-back manifest/archive hashes must match. GitHub release
and locally prepared metadata are not DOI evidence.

Current state remains:

```text
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```
