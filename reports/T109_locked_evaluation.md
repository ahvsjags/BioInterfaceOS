# T109 Execute one-shot locked 2025–2026 evaluation

## Result

T109 was completed on the KAUST Ibex server at implementation commit `96d9056`.
The evaluator verified the T108 signed release and executed one metadata-only
lockbox pass. The first-run output was sealed read-only. A second execution was
rejected before overwrite.

## Reproducible command

```bash
make lockbox-evaluate
```

Observed first run:

```text
LOCKBOX_EVALUATION_VALID release_id=bioif-internal-prelock-v1.0.0 predictions=5 replicated=2 refuted=1 inconclusive=2 abstentions=2 raw_values_written=false train_calls=0 tune_calls=0
```

Observed second-run protection:

```text
LOCKBOX_EVALUATION_INVALID: one-shot evaluation already executed; overwrite refused
```

## Sealed evaluator result

The evaluator processed five predeclared predictions. Two received `REPLICATED`,
one received `REFUTED`, and two received `INCONCLUSIVE`. Two predictions were
abstained. The output stores metric digests and failure classes only. It stores
no protected numeric values.

The operation log records release verification, prediction-metadata loading,
aggregate status emission, and receipt sealing. It records zero train calls,
zero tune calls, zero selection calls, and zero prediction rewrites.

## Acceptance evidence

| Gate | Result |
|---|---|
| Full test suite | 364 passed |
| Lock and environment | `uv lock --check` and frozen `uv sync` passed |
| Static checks | ruff check, ruff format check, mypy, compileall, and `git diff --check` passed |
| Repository checks | Schema, assets, catalog, lockbox, immutable releases, and project state passed |
| First-run protocol | 5 predictions evaluated; output sealed read-only |
| One-shot protection | Second run rejected; no overwrite occurred |
| Training/tuning firewall | train 0, tune 0, selection 0, prediction rewrites 0 |
| Protected boundary | raw values written false; protected values read false; lockbox payload unread |
| Contamination | Sealed evaluator results and operation log passed the configured forbidden-field/hash scan |

## Artifacts

- Schema: `agents/lockbox/evaluation_once.v1.json` (SHA-256 `f1fc39b74c5f3809b017529aa68f88d00d1c4c625e4cf4a2706375163e92aa5f`)
- Fixture: `tests/fixtures/lockbox/evaluate_fixture.json` (SHA-256 `db89575a1cf654695f4369874b020cae5f1797f57e984cf95cf404c6caa21b0c`)
- Workflow: `src/biointerfaceos/lockbox_evaluation_workflow.py` (SHA-256 `0d29b79751e17c52aedd0223ae4f269dfd39668c7d0365592f7d1580f7542b25`)
- Tests: `tests/lockbox/test_evaluation_workflow.py` (SHA-256 `8a45037ceb6c6eb9fea5a2945d4cf7762101e51ddf5841b23aa6084e8cf4cfd1`)
- Evaluator results: `reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/evaluation_results.json` (SHA-256 `c313b6ce19daeedcaff8b42138bd8b3bdcebc90f4c25ca5674032c1c0617efd6`)
- Operation log: `reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/operation_log.json` (SHA-256 `0f7b393ed369d10c306d2d55a03ad869c1efcad1dcf8528c924f7129717ef4ed`)
- First-run receipt: `reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/first_run_receipt.json` (SHA-256 `388ce2b36ed4f567e0baf5614260100d4cfdee36c2b446334e7822eaffd0234e`)

## Limitations

- The sealed evaluator output is metadata-only; it does not expose protected raw values.
- The first-run status is authoritative. No tuning or threshold changes were permitted.
- Any mechanical retry must preserve this receipt and follow a separate declared protocol.

The next task is T110: audit lockbox results and update claim statuses.
