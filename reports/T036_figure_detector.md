# T036 Scientific Figure Panel and Axis Detector Evidence

## Result

T036 is complete on the KAUST Ibex server. The deterministic fixture detector produces evidence-preserving panel and plot-feature candidates:

- figures: 2
- panels: 3
- supported 2D panels: 2
- unsupported panels: 1
- axes: 4
- legend entries: 3
- curve candidates: 3
- uncertainty cues: 2
- review-queue rows: 1

The detector identifies a linear x/y pair in panel A and infers a logarithmic x-axis from the 1/10/100 tick progression in panel B. Panel labels, normalized panel bounding boxes, axis tick positions, legend styles, curve candidate geometry summaries, uncertainty cues, confidence scores, and stable locators are retained. The heatmap panel is explicitly marked unsupported and routed to manual review.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 152 tests passed; ruff, format, and mypy passed.
- biointerfaceos extract figures --fixture: exit 0; figures=2 panels=3 supported_panels=2 unsupported_panels=1 axes=4 legend_entries=3 curve_candidates=3 uncertainty_cues=2 review_items=1.
- biointerfaceos extract tables --fixture: exit 0.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Eleven append-only ledgers validate, including task, search, expansion, family-review, download, table-review, and figure-review ledgers.
- Panel-label, normalized-bbox, linear/log-scale, legend, curve-candidate, uncertainty, confidence-calibration, unsupported-panel, no-digitization, and review-queue idempotency assertions passed.

## Limitations

- This task is a detector only; it does not digitize numeric points or infer experimental values.
- The fixture uses bounded vector-like evidence. Arbitrary raster segmentation and OCR are outside this task.
- Unsupported 3D, heatmap, and image-assay panels are retained for qualitative review.
- No live endpoints, binaries, credentials, repository code, locked-test payloads, or network data were accessed.

## Artifacts

- src/biointerfaceos/figure_detector.py
- tests/extract/test_figures.py
- tests/fixtures/figures/figure_detection.json
- registry/figure_detection.json
- registry/figure_review_queue.jsonl and its seal/snapshot
- reports/figure_detection.md
- docs/execplans/T036_figure_detector.md
- TASKS.tsv and PROJECT_STATE.yaml
- T036 sequence-32 record in reports/task_ledger.jsonl

## Commit

- aee17cf: detect figure panels and axes.
