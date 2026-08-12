# T120: Real open biointerface evidence with row-level provenance

## Purpose

Replace fixture-only support for empirical work with an auditable, openly licensed development-observation source. Every admitted measurement must resolve to a retained raw asset and original worksheet cell.

## Preconditions

T115–T117 are complete. The public-release registry remains default-deny, and R2 publication scope remains software/protocol-only.

## Non-goals

This task does not estimate an effect, fit a model, claim generalization, create a benchmark, or perform independent scientific validation.

## Interfaces and invariants

- Registry: `data/empirical/R2_EMPIRICAL_REGISTRY.json`.
- Command: `python -m biointerfaceos data audit-provenance --strict`.
- The audit checks anonymous public access, explicit reusable licence, source/study/laboratory/material/protocol lineage, raw byte size and SHA-256, worksheet/cell location, independent-unit label and raw numeric value.
- Evidence metadata is fixed to `DEVELOPMENT_OBSERVATION` and `EXPLORATORY`; generated receipts state that statistical conclusions, independent validation and scientific submission readiness are false.
- The output directory is append-only. Re-running against an existing receipt is refused.

## Implementation plan

1. Select an openly accessible raw-data record with a stable landing page and an explicit licence.
2. Retain the exact source files under the controlled empirical namespace and record their URLs, bytes and digests.
3. Implement a fail-closed workbook reader that verifies each registered observation against the original cell.
4. Add CLI, tests, licence-aware public asset classification, source policy and data dictionary.
5. Freeze the receipt only after strict audit, formatting, typing, tests and isolated public-release audit pass.

## Progress

- [x] 2026-08-12 — Verified University of Leeds dataset DOI `10.5518/1171`: anonymous public access, CC BY 4.0 and four XLSX raw-data files.
- [x] 2026-08-12 — Retained all four source workbooks with direct URLs, byte counts and SHA-256 values; registered 14 released GUV shrinking-rate observations.
- [x] 2026-08-12 — Implemented `EmpiricalProvenanceWorkflow`, strict CLI audit and immutable receipt.
- [x] 2026-08-12 — Remote validation passed: `ruff`, `mypy`, two focused tests, isolated strict provenance audit and isolated public-release audit.

## Discoveries

- The source contains a single study and laboratory. It is adequate for real-data admission and analysis-plan design, but it cannot meet the later multi-study, held-out and independent-evaluator gates.
- The Mendeley candidate examined during source scouting is CC BY 4.0 but exposes only a PDF asset in its public file listing; it was not admitted as a row-level raw-data source.

## Decisions

- Read the original XLSX cells at audit time instead of maintaining a hand-edited derived table. This makes a changed cell, label, digest or raw file fail the gate.
- Keep empirical source files controlled even when individually CC BY. They are explicitly excluded from the public software-replay source bundle until later evidence gates decide a data release scope.

## Validation

- `python -m biointerfaceos data audit-provenance --strict` → 1 source, 1 laboratory, 4 raw assets and 14 audited observations.
- `python -m biointerfaceos release audit-public --strict` in an isolated source tree → `PASS_PUBLIC_RELEASE_AUDIT`, with no classification ambiguity.
- `ruff format --check`, `ruff check`, `mypy`, and `pytest tests/data/test_empirical_provenance_workflow.py -q` all pass on KAUST.

## Failure recovery

If a licence, checksum, source URL, worksheet, independent-unit label or raw cell cannot be verified, remove the candidate from the empirical registry and preserve an exclusion reason. Do not substitute fixtures or a secondary summary.

## Outputs

- `data/empirical/R2_EMPIRICAL_REGISTRY.json`
- `data/raw/r2_empirical/leeds_1450/*.xlsx`
- `src/biointerfaceos/empirical_provenance_workflow.py`
- `reports/review_round_2/empirical_provenance/v1.1.0/`
- source policy, data dictionary and focused tests

## Completion note

T120 is complete as a data-admission gate. Its output is real development observation evidence only; T121 must freeze the analysis rules before any outcome analysis, and T122–T124 remain blocked on broader independent evidence.
