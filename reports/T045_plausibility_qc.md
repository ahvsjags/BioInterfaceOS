# T045 Physical and Statistical Plausibility QC Evidence

## Result

T045 is complete on the KAUST Ibex server. The fixture-backed QC checker preserves source values, emits deterministic rule flags, quarantines critical records, and retains warning records for manual review.

- records: 7
- flags: 5 (4 critical, 1 warning)
- quarantined records: 4
- clean-control false-positive records: 0
- clean-control false-positive rate: 0.000
- injected-error records: 4
- injected-error records flagged: 4
- injected-error recall: 1.000
- review-queue rows: 5

The rules cover fraction and percent bounds, non-negative concentration and dispersion, positive integer sample counts, duplicate sample counts, and candidate SEM/SD label confusion. The warning carries weight 0.5; critical flags carry weight 1.0.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 181 tests passed; ruff, format, and mypy passed.
- biointerfaceos qc records --fixture --strict: exit 0; records=7 flags=5 critical_flags=4 warning_flags=1 quarantined_records=4 false_positive_controls=0 injected_error_recall=1.000 review_items=5.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed; tasks=115.
- compileall and git diff --check: passed.
- All append-only JSONL ledgers validate, including the new QC review queue.

## Artifacts

- src/biointerfaceos/plausibility_qc.py
- src/biointerfaceos/cli.py
- tests/fixtures/qc/records.json
- tests/qc/test_records.py
- registry/qc_flags.json
- registry/qc_quarantine.json
- registry/qc_review_queue.jsonl and its seal/snapshot
- reports/qc_metrics.json (SHA-256: cad5a2257d96ff041e6c82d284e3b95feee32e0cc156434fc38d3f951d89fb5c)
- reports/qc_records.md (SHA-256: f9cea82846387e2db6e77bdeafebb16e3f6c06838a605b2b7ea8a1699d53b299)
- docs/execplans/T045_plausibility_qc.md
- sequence-41 record in reports/task_ledger.jsonl

## Limitations

- Rules are deterministic and fixture-backed; no live study records were accessed.
- Warnings identify review candidates and are not accepted scientific results.
- No raw source value is silently corrected or overwritten.
