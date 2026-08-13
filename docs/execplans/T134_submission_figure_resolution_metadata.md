# T134: Correct embedded PNG resolution metadata in R2 protocol figures

## Purpose

Correct a release-technical discrepancy found by an independent visual and
file-metadata review: the v1.1.0 R2 PNG exports had 3,780 x 2,126 pixels from a
600-dpi conversion, but did not carry a PNG `pHYs` resolution chunk.  The
historical v1.1.0 receipt remains immutable.  This task issues a versioned
v1.2.0 figure suite with explicit physical-resolution metadata.

## Scope and invariants

- Re-render from the field-mapped SVG specification; never resample or edit a
  prior PNG.
- Each PNG must include exactly one `pHYs` chunk immediately after `IHDR`, with
  x/y resolution `23,622` pixels per metre and unit `metre` (the integer PNG
  representation of 600 dpi).
- The geometry, semantic and protocol-only gates remain mandatory.  Embedded
  DPI metadata does not promote the figures to scientific results or
  submission-ready evidence.
- All dependent current receipts are regenerated in new directories; prior
  v1.1.0--v1.8.0 receipts are retained unmodified for audit history.

## Validation

```bash
python -m biointerfaceos publication render-r2 --strict
python -m biointerfaceos release audit-public --strict
python -m biointerfaceos reproduce release --strict
python -m biointerfaceos manuscript audit-portfolio --strict
python -m biointerfaceos project accept-r2 --strict
python -m biointerfaceos project audit-r2-remediation --strict
python -m biointerfaceos project audit-r2-external-handoff --strict
python -m pytest tests/publication/test_submission_figure_qa_workflow.py -q
```

## Acceptance evidence

- `reports/review_round_2/submission_figures/v1.2.0/` with `pHYs`-verified
  QA cards and 600-dpi PNG exports.
- Current public-release, software-replay, manuscript-portfolio, acceptance,
  remediation and external-handoff receipts bound to the versioned output.

## Completion note

Pending KAUST rendering and full receipt verification.
