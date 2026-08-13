# T135: Fail-closed external source-intake preflight

## Purpose

Turn T133's field-level handoff contract into a contributor-run preflight that
checks a submitted source manifest against the received file bytes.  This task
does not receive a source, contact an external party, approve a licence,
admit a target, amend T121 or create a scientific result.

## Preconditions and scope

T133 is complete and fixes the active CC0-only route, required analysis-unit
fields and independent-evaluation boundary.  A future contributor retains
source files outside the repository and supplies their own manifest plus an
assets directory.  The template is deliberately not a submission and must be
rejected by the preflight command until it is completed externally.

## Invariants

- Every declared asset uses a relative POSIX path below the supplied assets
  root, exists locally and matches its declared SHA-256.  The same asset hash
  cannot be counted for two submitted source records.
- Each analysis unit identifies one declared asset and repeats its verified
  checksum; unit IDs are globally unique.
- The submission declares CC0-1.0, a human biofluid, a segregated author
  scale, a finite numeric material/size covariate, biological and replicate
  roles, one endpoint unit/scale and one preprocessing version.
- At least two distinct laboratory affiliations are mandatory.  The command
  validates that declaration structurally, not the truth of an affiliation,
  licence or scientific measurement.
- A successful return is only
  `STRUCTURALLY_COMPLETE_REQUIRES_SOURCE_AUDIT`; it never means target
  admitted, T121 amended, model fitted, evaluator verified or submission ready.

## Interface

```bash
python -m biointerfaceos data preflight-external-source-intake \
  --manifest /secure/incoming/source-intake.json \
  --assets-root /secure/incoming/assets --strict
```

The manifest shape is documented in
`schemas/external_source_intake.schema.json`; use
`docs/data/R2_EXTERNAL_SOURCE_INTAKE_TEMPLATE.json` as a blank starting
point.  Do not commit incoming source files, protected values or external
identity attestations to this repository.

## Acceptance evidence

- `src/biointerfaceos/external_source_intake.py`.
- `schemas/external_source_intake.schema.json`.
- The explicitly non-submittable template and this execution plan.
- Regression tests covering a synthetic structural package and rejection of a
  template, single-laboratory submission, checksum mutation and path escape.

## Completion note

The intake gate is implemented.  Its completion is an infrastructure result
only; T129 remains in progress and T123--T128 remain externally gated.
