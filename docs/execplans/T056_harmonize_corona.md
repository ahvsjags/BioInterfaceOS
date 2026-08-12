# T056: Harmonize protein-corona matrices across projects

## Purpose

Align the T055 protein-by-sample matrices with project-level protein-corona metadata and mappings, preserving project-specific scales while producing auditable composition/function matrices and batch metadata.

## Preconditions

T042 material and study contracts, T052 PRIDE project/sample plans, and T055 LFQ outputs are complete. Each project must retain its own sample/run provenance, protein-group mapping, species context, and outcome scale.

## Non-goals

This task will not apply ComBat or any batch correction that could leak outcome labels, force unrelated projects into one quantitative scale, or collapse ambiguous protein groups into false single-protein identities.

## Interfaces and invariants

Every harmonized row will retain project accession, source matrix hash, species/protein mapping status, normalization route, compositional transform, and missingness status. Project-level matrices remain separately inspectable. Cross-project summaries may use shared functional modules only when protein mapping and measurement scale are explicit.

## Implementation plan

1. Define a fixture with two project matrices, project-specific scales, protein mappings, material/outcome metadata, and functional module annotations.
2. Validate T055 matrix and protein-group hashes before harmonization; reject stale or ambiguous mappings.
3. Normalize within project using a declared compositional representation and preserve the original project scale.
4. Build auditable protein and functional-module matrices with project/batch columns and explicit missingness.
5. Add `biointerfaceos omics harmonize-corona` with no-ComBat and no-outcome-leakage checks.
6. Add focused tests, evidence report, deterministic receipts, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics harmonize-corona`
- project-level scale preservation and mapping-audit assertions
- compositional transform and missingness checks
- explicit no-ComBat and no-outcome-leakage assertions
- `biointerfaceos assets verify`
- `biointerfaceos catalog check`
- `biointerfaceos lockbox self-test`
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`
- `biointerfaceos state validate`
- `python -m compileall -q src tests`
- `git diff --check`

## Failure recovery

If a protein mapping is species-ambiguous or a project scale cannot be retained, quarantine that row/project with a reason and continue only with auditable functional modules. If a transform would mix outcomes or project batches, stop before harmonization and preserve the project-level matrices.

## Outputs

Project matrix audit, mapping table, project-preserved normalized matrices, functional-module matrix, batch metadata, missingness report, QC/guard report, deterministic receipts/logs, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
