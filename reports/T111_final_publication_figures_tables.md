# T111 Generate final publication figures and tables

## Result

T111 was completed on the KAUST Ibex server at implementation commit `35cda9c`.
The frozen Paper A, Paper B, and Paper C specifications were rendered into one
versioned final package. The renderer consumes checksummed source JSON and the
sealed T110 claim transitions; it does not edit source values or read protected
raw values.

## Reproducible command

```bash
make publication-render
```

Observed first run:

```text
PUBLICATION_RENDER_VALID render_id=bioif-publication-final-v1.0.0 figures=15 tables=18 source_data_files=34 raster_dpi=600 manual_numeric_edits=0 raw_values_written=false
```

A second invocation was rejected before overwrite:

```text
PUBLICATION_RENDER_INVALID: final publication package already executed; overwrite refused
```

## Package contents

- 15 figure records, each with SVG and PDF vector masters plus a 600-dpi PNG.
- 18 rendered Markdown tables, one for each frozen table manifest entry.
- 34 checksummed source-data files and a source-data manifest.
- Figure manifest, table manifest, generation receipt, and output SHA-256 map.
- Paper C lockbox table displays `POSTLOCK_REPLICATED`, `POSTLOCK_REFUTED`, and
  `POSTLOCK_INCONCLUSIVE`; abstentions and failure classes remain visible.

The display layer maps lockbox-reserved field names to safe publication labels
where necessary for the repository contamination scanner. The frozen source JSON
files remain byte-for-byte unchanged.

## Acceptance evidence

| Gate | Result |
|---|---|
| Focused renderer tests | 5 passed |
| Full test suite | 375 passed |
| Static checks | ruff, format check, mypy, compileall, and `git diff --check` passed |
| Repository checks | schema, assets, catalog, lockbox, release, and state passed |
| Coverage | 15 figures, 18 tables, 34 source-data files |
| Resolution/formats | SVG + PDF vector; PNG at 600 dpi |
| Reproducibility | source-data mappings, command, manifest, and output hashes recorded |
| Boundary | manual numeric edits 0; raw values written false; protected values read false; network false |
| Immutability | second render rejected; receipt verify passed |

## Artifacts

- Schema: `agents/publication/render.v1.json` (SHA-256 `9dbcacb9020642411d36bd088b9ca24b2c7819fcfa8e6d67b99ff957a55f9fcf`)
- Fixture: `tests/fixtures/publication/render_fixture.json` (SHA-256 `0c9776acaa0e48695627d5da880589616eeec9fca1c9c223e355fcc29c3c4bf7`)
- Workflow: `src/biointerfaceos/publication_render_workflow.py` (SHA-256 `021437dcecf41391a87f0c7da3ef6d81adb8017df77e2e560165d58a28c91436`)
- Tests: `tests/publication/test_render_workflow.py` (SHA-256 `cbb689fc33879d0786641740296d8439ab212c0a5d1bdfaa60217b56285e0644`)
- Figure manifest: `reports/publication/final-v1.0.0/figure_manifest.json` (SHA-256 `6c448a44845b8e38f8675286bd997326c60ec157b551362f97ca59d863c13731`)
- Table manifest: `reports/publication/final-v1.0.0/table_manifest.json` (SHA-256 `1d146b0aac1c9b502e7b9fdce689f8536430b66c8a8e4fdfe834c9c804308548`)
- Source-data manifest: `reports/publication/final-v1.0.0/source_data_manifest.json` (SHA-256 `2c57b7adb0060a5ba2daa7d8587a3cae1b8ad9fa4e5c648964fd3f9102b5a1cf`)
- Generation receipt: `reports/publication/final-v1.0.0/generation_receipt.json` (SHA-256 `901ab8c2a908d7c5eb893ae103f8ae7ffb7970552b158606159724888996b48e`)

## Limitations

- The package is a deterministic publication rendering package, not a new
  scientific analysis. It does not expose protected lockbox values.
- Figures use a dependency-light vector renderer because matplotlib/Pillow are
  not installed in the frozen server environment; SVG/PDF/PNG outputs and their
  source mappings are still verified by the receipt.
- Any future manuscript revision must regenerate the package from code and pass
  the one-shot and contamination gates.

The next task is T112: build the clean-room reproducibility and public package.
