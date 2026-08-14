# External user task catalog — r10.45

Two distinct non-author users or institutions must complete different real-data
tasks from the same immutable release. Clean checkout, environment digest,
commands, stdout/stderr, output hashes, limitations, failures and a signed
receipt are required for each task.

## Task A — independent public-data reproduction

Use `scripts/r4_external_reproduction_r10_45.sh`. It clones the fixed release,
reacquires and hashes PMC6592156 supplementary data, runs the source audit and
paper-attached OOD, and writes a fresh execution bundle.

## Task B — provenance and endpoint audit

```bash
uv sync --locked --all-groups
uv run biointerfaceos data verify-r4-t249-four-lab-common-target --strict
uv run biointerfaceos data verify-r4-t258-source-unit-endpoint-license --strict
```

The user must explain the four source anchors, seven-target freeze, pairwise
endpoint interpretation, technical replicate policy and license/source locator
audit. Task B is not a model-performance rerun and is materially distinct from
Task A.

The catalog makes external work executable; it is not evidence of adoption.
