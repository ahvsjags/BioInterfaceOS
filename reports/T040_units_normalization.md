# T040 Units Normalization and Uncertainty Evidence

## Result

T040 is complete on the KAUST Ibex server. The deterministic unit registry handles length, time, concentration, dose, zeta potential, and PDI while preserving raw evidence:

- assertions: 8
- normalized: 6
- clarification/review rows: 2
- uncertainty-bearing assertions: 5

Valid conversions preserve raw value/unit, normalized value/unit, dimension, factor, relative uncertainty, and exact evidence locator. An mg-to-mg/kg assertion without basis remains unnormalized with UNKNOWN_BASIS_FOR_DOSE. An hour-to-nanometer conversion remains unnormalized with INCOMPATIBLE_DIMENSIONS. Neither case is guessed or silently coerced.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 166 tests passed; ruff, format, and mypy passed.
- biointerfaceos normalize units --fixture: exit 0; assertions=8 normalized=6 review_items=2 uncertainty_records=5.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Fifteen append-only ledgers validate, including task, search, expansion, family-review, download, table, figure, digitization, consensus, evidence, and unit-review ledgers.
- Dimension conversions, raw-value retention, uncertainty factor propagation, unknown-basis firewall, incompatible-dimension block, and clarification-queue assertions passed.

## Limitations

- The registry is deterministic and fixture-backed; unsupported units remain review-only.
- Dose conversion from a mass value requires an explicit basis and is not inferred.
- No live endpoints, binaries, credentials, repository code, locked-test payloads, or network data were accessed.

## Artifacts

- src/biointerfaceos/unit_normalizer.py
- tests/normalize/test_units.py
- tests/fixtures/normalize/units.json
- registry/normalized_units.json
- registry/unit_clarification_queue.jsonl and its seal/snapshot
- reports/unit_normalization.md
- docs/execplans/T040_units_normalization.md
- TASKS.tsv and PROJECT_STATE.yaml
- T040 sequence-36 record in reports/task_ledger.jsonl

## Commit

- bb0b1f9: normalize units with basis firewall.
