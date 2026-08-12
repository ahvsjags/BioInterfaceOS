# T111 Generate final publication figures and tables

## Objective

Generate the final publication figure and table package from the frozen Paper A,
Paper B, and Paper C specifications plus the sealed T109/T110 metadata. Every
panel and cell must be reproducible from repository code, source-data files,
and a recorded command. No manual numeric editing or protected raw-value access
is permitted.

## Scope

- Convert approved figure specifications into deterministic publication assets.
- Convert approved table manifests into source-data tables and rendered tables.
- Include replicated, refuted, inconclusive, and abstained lockbox statuses where
  they are part of the displayed evidence.
- Preserve C6 association-only language and C7 OOD/selection applicability limits.
- Produce vector outputs and 600-dpi raster exports where the format supports it.
- Write a figure/table manifest, source-data manifest, checksums, and generation
  receipt under a versioned final-publication directory.

## Implementation steps

1. Add a versioned figure/table generation schema and fixture.
2. Implement deterministic `publication render --strict` with input hashes,
   figure/table coverage, status-boundary checks, and contamination scanning.
3. Add focused tests for panel/cell coverage, status visibility, unsupported
   claims, missing source data, and output tampering.
4. Add the CLI command and `make publication-render` target.
5. Generate the final package and verify all assets from source data.
6. Record T111 and activate T112 only after every output has a receipt and hash.

## Acceptance criteria

- Every approved figure and table has a deterministic source-data mapping.
- Every numeric cell has a source-data row and generating command.
- Vector/SVG and 600-dpi raster outputs are present where applicable.
- No protected raw values, network downloads, or manual number edits occur.
- C1-C5 status labels and C6-C8 wording/applicability restrictions remain
  visible and auditable.
- Manifest, checksums, receipt, and contamination scan all pass.

## Fallback

Omit or mark any panel that lacks auditable source data. Do not interpolate,
repair, or replace missing values with hand-entered numbers. Preserve
inconclusive/refuted/abstained statuses rather than visually upgrading them.
