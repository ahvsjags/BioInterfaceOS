# T006: Implement project state and append-only ledgers

## Purpose

Create a typed, deterministic state/DAG validator and tamper-evident append-only JSONL storage needed for safe autonomous task resumption.

## Preconditions

T000 through T005 are DONE, T004 is T006's satisfied dependency, T006 is current, T007 remains READY, the worktree began clean, and no scientific data are needed.

## Non-goals

This task does not implement T007 schemas or any later data, model, release, lockbox, or scientific feature. It does not access locked-test or external data.

## Interfaces and invariants

`biointerfaceos state validate` validates `PROJECT_STATE.yaml`, `TASKS.tsv`, DAG acyclicity, dependency/status coherence, and project-state/task-state agreement. `biointerfaceos state next` prints exactly one deterministic dependency-satisfied task. State transitions use an explicit allowlist; `DONE` requires a prior `IN_PROGRESS` state, satisfied dependencies, and acceptance evidence. New JSONL records are canonicalized, hash-chained, atomically sealed, and recoverable from a sealed snapshot. Existing history is never overwritten during initialization. Recovery first creates a unique quarantine copy.

## Implementation plan

1. Mark T006 in progress and create this plan.
2. Pin PyYAML and add typed state/task parsing, DAG validation, transition validation, and CLI dispatch.
3. Add append-only ledger initialization, chained writes, seals, validation, quarantine, and recovery.
4. Add offline unit tests covering valid/invalid state, deterministic selection, DONE rules, tamper/truncation detection, initialization, and crash/resume recovery.
5. Run the lock, frozen sync, quality, CLI acceptance, focused tests, compileall, and containment checks.
6. Record evidence, advance T006/T007 state, append exactly one hashed T006 completion record, update this plan, and commit focused changes with an evidence follow-up if required.

## Progress

- [x] 2026-08-11 — Read repository rules, goal, planning standard, state, T006/T007 rows, prior plan/ledger conventions, and current CLI.
- [x] 2026-08-11 — Marked T006 IN_PROGRESS and made this the active ExecPlan.
- [ ] Implement state, ledger, CLI, tests, and initial ledgers.
- [ ] Run all acceptance and containment checks.
- [ ] Record completion state, evidence, ledger record, and commits.

## Discoveries

The task ledger has six pre-T006 records without per-line integrity metadata. They are an immutable legacy prefix: T006 will preserve their bytes, seal the entire file, and hash-chain every new record from the preceding physical line.

## Decisions

Use exactly pinned PyYAML for safe YAML parsing. Keep JSONL records as user-visible objects with reserved `_ledger` integrity metadata, and use atomic sidecar seal/snapshot files so interrupted metadata writes cannot damage the append-only history.

## Validation

- `uv lock --check`
- `uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `.venv/bin/biointerfaceos state validate`
- `.venv/bin/biointerfaceos state next`
- `.venv/bin/python -m unittest tests.test_state_ledgers -v`
- `.venv/bin/python -m compileall -q src tests`
- `git diff --check` and repository containment assertions

Every command must exit zero; the focused recovery tests must prove quarantine and byte-exact restoration after truncation and rewrite corruption.

## Failure recovery

Do not update T006 to DONE until all gates pass. A ledger integrity failure is copied to a collision-resistant quarantine path before the writer restores the last valid sealed snapshot; recovery never overwrites an earlier quarantine artifact. Interrupted appends are treated as corruption and follow the same path.

## Outputs

State/ledger module, CLI integration, pinned dependency/lock, focused tests, initialized decision/blocker/experiment JSONL ledgers with seals, this ExecPlan, `reports/T006_state.md`, task/state updates, one T006 ledger record, and focused commits.

## Completion note

Pending verification.
