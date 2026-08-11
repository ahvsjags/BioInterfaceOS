# T047: Build normalized Silver data release

## Purpose

Assemble normalized analytical tables from the Bronze release and completed ontology/QC registries while preserving evidence locators, quarantine boundaries, primary-key uniqueness, and schema/version hashes.

## Preconditions

T039 through T046 are DONE. Evidence, unit, material, protein, protocol, endpoint, plausibility-QC, and immutable Bronze artifacts are available.

## Non-goals

This task will not silently drop records, overwrite Bronze bytes, accept critical QC rows, or harmonize incompatible units, bases, assays, or timepoints.

## Interfaces and invariants

Every Silver value must retain a source locator and normalization lineage. Primary keys are deterministic and unique. Quarantined or unresolved rows remain explicitly represented in review/quarantine outputs. The schema hash and catalog metadata are frozen in the release receipt.

## Implementation plan

1. Inspect Bronze manifests and all normalized registries for stable join keys and evidence locators.
2. Define fixture-backed Silver table schemas for materials, proteins, protocols, endpoints, and experiment records.
3. Implement deterministic referential-integrity, duplicate-key, evidence-coverage, and critical-QC gates.
4. Write Parquet tables and catalog views without modifying Bronze inputs.
5. Add biointerfaceos data build-silver and data validate silver commands with focused tests.
6. Run the full acceptance gates and append evidence to the task ledger.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos data build-silver --fixture
- biointerfaceos data validate silver --fixture
- biointerfaceos release verify bronze
- biointerfaceos assets verify
- biointerfaceos catalog check
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- referential-integrity, unique-key, evidence-coverage, quarantine, and schema-hash assertions

## Failure recovery

Keep Bronze immutable. Quarantine rows with missing evidence or critical QC and repair mappings before rebuilding Silver. Never silently discard a row.

## Outputs

Silver Parquet tables, catalog views, QC/integrity report, schema hash, fixture/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
