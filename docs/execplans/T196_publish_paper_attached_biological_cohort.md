# T196 — Publish the paper-attached biological cohort for clean reproduction

## Objective

Promote the already audited, explicitly CC-BY-4.0 paper-attached PXD017052
Supplementary Data 5 and its row-level source-cell map into the public
empirical candidate. This supplies a real biological-unit OOD route without
relabeling it as a new laboratory, protected lockbox, or non-author result.

## Frozen evidence boundary

- Source: DOI `10.1038/s41467-020-17033-7`, paper-attached Supplementary Data 5.
- License: CC-BY-4.0 as recorded by the T180 source registry.
- Biological units: 141 individual subject plasma samples.
- Measurements: 705 subject-by-particle batches; 666 batches meet the
  predeclared minimum of 10 positive frozen-target proteins.
- Public assets: the original workbook and the derived row-level map, each
  checked by SHA-256 and tied to T180/T181 receipts.
- Claim boundary: author-run exploratory biological-cohort OOD. It is not an
  independent laboratory anchor, protected lockbox evaluation, no-author
  reproduction, or scientific-submission gate.

## Execution and acceptance

1. Verify T180 source and T181 biological OOD receipts from the clean checkout.
2. Add only the explicitly redistributable workbook and derived map to the
   release manifest; keep unrelated analysis-only candidates out of the tag.
3. Run the full review-round test suite, the T180/T181 strict verification
   commands, compileall, and the manifest hash audit on KAUST.
4. Publish an immutable tag whose manifest resolves to the containing commit.

## Reproducibility commands

```bash
uv run biointerfaceos data verify-r4-pxd017052-nsclc-source \
  --assets-root data/raw/r4_candidate_pxd017052_nsclc --strict
uv run biointerfaceos data verify-r4-pxd017052-nsclc-biological-ood --strict
```

The release remains `scientific_submission_ready=false` until a real
non-author lockbox receipt, no-author scientific reproduction, external users,
and DOI archive receipt exist.
