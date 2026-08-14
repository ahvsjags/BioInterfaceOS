# R4-T243: Execution-pack state graph repair

Date: 2026-08-14
Status: `TASK_LEDGER_AND_PROJECT_STATE_VALIDATED_EXTERNAL_GATES_UNCHANGED`

## Finding

The full local test run exposed an execution-pack integrity defect that was independent of the paper-data analysis: 28 task rows from T188 through T225 had no final `failure_policy` field. The same ledger also retained dependencies on historical task IDs that are not present in the current append-only task file (`T156`, `T162`, `T166`, `T167`, and `T179`). Those defects prevented state validation before downstream acceptance tests could run.

## Remediation

- Added an explicit failure policy to every affected task: failed and negative runs remain preserved, and evidence/claim/readiness gates may not be weakened.
- Removed dangling historical dependencies while retaining the available current task prerequisites.
- Removed dependencies on still-active umbrella tasks from already-completed derived audits so completed tasks do not claim unsatisfied prerequisites.
- Marked T219 and T220 `BLOCKED`, reflecting their genuine dependence on the still-missing external evidence bundle rather than presenting them as ready.
- Updated `PROJECT_STATE.yaml` to 188 tasks and regenerated completed/blocked summaries from the task ledger.
- Kept T218 as the current `IN_PROGRESS` external-evidence task and kept T123 as the only `READY` task.

## Verification

```text
task_count=188 validated=188 current=T218
13 passed: tests/test_state_ledgers.py tests/acceptance/test_final_acceptance_workflow.py
```

The full-suite run remains useful as a failure inventory: the state-graph errors are resolved, while unrelated agent/release/Windows-fixture failures and the repository-wide Ruff baseline remain separate engineering work.

## Claim boundary

This repair changes task bookkeeping and failure-policy enforcement only. It creates no scientific observation, evaluator receipt, external reproduction, adoption record, DOI archive, or submission-ready claim. All external gates and `scientific_submission_ready` remain false.
