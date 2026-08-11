# T007: Define canonical schemas and configuration validation

## Purpose

Define versioned, machine-checkable contracts for the nine T007 scientific objects and provide deterministic, repository-contained YAML configuration validation without adding dependencies.

## Preconditions

T000 through T006 are DONE, T004 is satisfied, T007 is READY/current, PyYAML 6.0.2 is pinned and available offline, and the T006 append-only task-ledger writer is operational.

## Non-goals

This task does not implement storage accounting, networking, ingestion, modeling, agents, claims analysis, releases, or locked-test access. It does not download data or add dependencies.

## Interfaces and invariants

Version 1 JSON Schema documents live at `schemas/<object>.v1.json`. `biointerfaceos schema validate-all` validates every contractual schema and repository fixture, returning nonzero with field paths on any error. YAML fixtures use a strict `schema`, `schema_version`, `data` envelope. Loading uses `yaml.safe_load`; requested config and schema paths must resolve inside the repository. Unknown fields, missing required fields, primitive type mismatches, and enum violations are rejected deterministically. JSON booleans are not integers.

## Implementation plan

1. Add this ExecPlan and inspect the T007 contract and T006 interfaces.
2. Add nine versioned JSON Schema files and representative offline YAML fixtures.
3. Implement typed schema discovery, schema sanity checks, recursive instance validation, safe YAML loading, containment, and CLI dispatch.
4. Add focused tests for success, field paths, types, enums, unknown fields, versions, malformed schemas/YAML, and containment.
5. Run all requested acceptance and containment gates.
6. After every gate passes, write the evidence report, advance task/state status, append exactly one T007 ledger record with `AppendOnlyJSONL`, update this plan, and commit.

## Progress

- [x] 2026-08-11 — Read AGENTS.md, GOAL.md, PLANS.md, PROJECT_STATE.yaml, T007/T008/T009 task rows, the active T006 ExecPlan/evidence, and relevant foundation source/tests.
- [x] 2026-08-12 ? Implemented nine versioned JSON Schemas, strict YAML config loading, recursive validation, CLI dispatch, fixtures, and focused tests.
- [x] 2026-08-12 ? Ran lock check, offline frozen sync, make check, schema validate-all, focused tests, state validation, compileall, and containment checks successfully.
- [x] 2026-08-12 ? Recorded the T007 evidence report and task-ledger entry, advanced T007/T008/T009 state, and committed the result.

## Discoveries

The pinned environment intentionally has no general JSON Schema library. T007 therefore needs a small supported-keyword validator covering the contract's required fields, primitive types, arrays, enums, numeric bounds, and closed objects.

## Decisions

Use JSON Schema draft 2020-12 documents as portable artifacts while implementing only the deterministic subset used by these contracts. Keep configuration metadata outside scientific payloads in a strict envelope so schema/version selection cannot be confused with domain fields.

## Validation

- `uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `.venv/bin/biointerfaceos schema validate-all`
- `.venv/bin/python -m pytest -q tests/test_schema_config.py`
- `.venv/bin/python -m compileall -q src tests`
- `git diff --check` plus repository-containment assertions

All commands must exit zero. Focused tests must also prove invalid schemas and fixtures return nonzero and errors include field paths.

## Failure recovery

Do not mark T007 DONE or append its ledger record until every gate passes. Schema/config validation is read-only. Preserve T006 ledger bytes and metadata; if final ledger append fails, use the existing sealed recovery procedure and retain quarantine evidence.

## Outputs

Nine schemas, schema/config module, CLI command, offline fixtures, focused tests, this ExecPlan, `reports/T007_schemas.md`, task/state advancement, exactly one T007 task-ledger record, and one focused commit.

## Completion note

T007 is complete. Nine version-one JSON Schema contracts, strict repository-contained YAML envelopes, field-path validation, offline fixtures, and the schema validate-all CLI passed the full quality and focused test gates. T008 and T009 are READY; T008 is current. No data, model, or locked-test payload was accessed.
