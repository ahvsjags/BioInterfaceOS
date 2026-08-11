# Paste this into Codex after placing the execution pack at the repository root

Read `AGENTS.md`, `GOAL.md`, `PLANS.md`, `PROJECT_STATE.yaml`, and `TASKS.tsv` completely. Treat `GOAL.md` as the project contract and `TASKS.tsv` as the dependency-ordered execution queue.

Initialize or repair the repository so that the first incomplete, dependency-satisfied task can be executed. Then enter the following loop within this session:

1. select the first dependency-satisfied task whose status is not `DONE` or `WAIVED`;
2. create/update its ExecPlan under `docs/execplans/`;
3. implement the task completely;
4. run all task-specific and repository-wide acceptance checks that apply;
5. preserve logs, failed attempts and evidence;
6. update `PROJECT_STATE.yaml`, `reports/task_ledger.jsonl`, `reports/DECISIONS.md`, and `TASKS.tsv`;
7. make a focused git commit;
8. continue to the next dependency-satisfied task.

Do not stop merely because one source is inaccessible. Any source requiring registration, login, approval, API key, payment or data-use agreement must be rejected and replaced by an anonymous public source. Do not claim human expert review unless a signed review file exists. Do not inspect or download the locked 2025-01-01 through 2026-08-11 evaluation content before the freeze task. Never fabricate values, citations, licenses, successful tests or scientific conclusions.

Only pause for an action that is genuinely impossible or unsafe to resolve inside the repository, such as a destructive operation outside the project root, a legal ambiguity that cannot be quarantined, or unavailable compute needed for a mandatory final run. In that case, record the exact blocker and continue every independent task first.
