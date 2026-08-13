# R4 R9 public release and DOI status

Status: `PUBLIC_VERSION_RELEASED_DOI_PENDING`

## Release target

- repository: `https://github.com/ahvsjags/BioInterfaceOS`
- branch: `r3-real-data-execution-20260813`
- immutable tag: `v0.1.3-r9`
- release scope: T180/T181 source registry, protocol, source-cell map, model/OOD receipts, tests, and external handoff documentation;
- raw candidate folders under `data/raw/` remain outside the tracked public release unless their source licence and redistribution status are explicitly admitted.

The R9 release is a provenance and handoff improvement. T180/T181 remain author-run, same-laboratory exploratory evidence. They do not constitute protected lockbox evaluation, non-author scientific reproduction, clinical validation, or community adoption.

## DOI gate

`doi_status` remains `PENDING_NOT_ARCHIVED`. A GitHub tag or release is not a DOI and cannot substitute for an archival receipt. `CITATION.cff` therefore names the R9 version while explicitly stating that archival verification is pending. The DOI may change to `ARCHIVED_VERIFIED` only after Zenodo or an equivalent archival service returns an immutable record, archived version, and content hash that match the release.

## Scientific gates

The following flags remain false:

```text
independent_validation=false
external_scientific_reproduction=false
scientific_submission_ready=false
```

The remaining gates are external to the author-controlled repository: one real non-author protected lockbox receipt, one no-author end-to-end scientific reproduction, at least two independently verifiable adoption receipts, and an archival DOI receipt. Structural preflight documents remain templates until real submissions arrive.

## Verification

```bash
git clone --branch v0.1.3-r9 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
uv sync --locked --all-groups
uv run pytest -q tests/review_round_3 tests/review_round_4
uv run biointerfaceos data verify-r4-pxd017052-nsclc-source --assets-root data/raw/r4_candidate_pxd017052_nsclc --strict
uv run biointerfaceos data verify-r4-pxd017052-nsclc-biological-ood --strict
```

The source workbook is not redistributed by this release; an evaluator must reacquire or attest it through the source locator under the T180 registry and submit the required aggregate receipt.
