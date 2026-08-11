# T037 Figure Digitization and Uncertainty Evidence

## Result

T037 is complete on the KAUST Ibex server. Eligible detector candidates are calibrated and digitized with explicit provenance:

- figures: 1
- panels: 2
- series seen: 5
- digitized series: 4
- excluded low-quality series: 1
- digitized points: 12
- uncertainty records: 4
- review-queue rows: 1

Curve, bar, and scatter candidates are all represented. Linear calibration recovers the known values in panel D, while the logarithmic x-axis in panel E maps its midpoint to 10.0. Error bars propagate through the y-axis transform and retain SD/SE labels. Every point preserves a detector locator and a stable digitized-point locator. A JSON QC overlay maps normalized candidate coordinates to calibrated output locators. The low-resolution series is quarantined and never promoted.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 156 tests passed; ruff, format, and mypy passed.
- biointerfaceos extract figures --fixture --digitize: exit 0; detection and digitization summaries passed.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Twelve append-only ledgers validate, including task, search, expansion, family-review, download, table-review, figure-review, and digitization-review ledgers.
- Synthetic recovery, linear/log calibration, residual, curve/bar/scatter, uncertainty propagation, QC overlay, detector-locator, low-quality exclusion, and review-queue idempotency assertions passed.

## Limitations

- Digitization is fixture-backed and limited to normalized vector-like candidate coordinates.
- Unsupported panel types and candidates below the quality threshold remain qualitative/review-only.
- No automatic raster OCR, hidden payload access, or live network data was used.
- Numeric output is emitted only after an explicit calibration record and residual check.

## Artifacts

- src/biointerfaceos/figure_digitizer.py
- tests/extract/test_digitize.py
- tests/fixtures/figures/digitization.json
- registry/digitized_figure_points.json
- registry/digitization_review_queue.jsonl and its seal/snapshot
- reports/digitization_qc_overlay.json
- reports/figure_digitization.md
- docs/execplans/T037_digitization.md
- TASKS.tsv and PROJECT_STATE.yaml
- T037 sequence-33 record in reports/task_ledger.jsonl

## Commit

- 8e4388b: digitize figure candidates with uncertainty.
