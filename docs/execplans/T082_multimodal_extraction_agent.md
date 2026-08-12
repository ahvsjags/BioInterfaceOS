# T082 Multimodal ExtractionAgent

## Purpose

Implement a typed ExtractionAgent that selects an appropriate parser for document/table/figure cases, emits schema-valid evidence-grounded experiment records, and is accepted only if it improves the declared extraction metric over the fixed pipeline.

## Preconditions

T080 typed runtime, T038 extraction foundations, T050 dual extraction, schema contracts, and gold cases are valid. Existing fixed extraction remains the reference fallback.

## Non-goals

This task will not invent values without evidence, bypass parser failures, lower the gold-case acceptance threshold, or accept an agent solely because it produces more records.

## Interfaces and invariants

`biointerfaceos agent eval extraction` will run parser selection over deterministic gold cases, emit tool traces and schema-valid experiment records with evidence locators, compare agent and fixed-pipeline metrics, and retain the fixed pipeline if agent value is non-positive.

## Implementation plan

1. Define typed extraction cases, parser-selection decisions, evidence-grounded records, and metric cards.
2. Route table, figure, supplement, and born-digital cases through allowlisted deterministic parser tools.
3. Validate every emitted record against the existing experiment/evidence contracts and retain failures.
4. Compare agent accuracy/completeness against the fixed pipeline; apply the declared acceptance gate.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos agent eval extraction`
- parser selection, schema validation, evidence locators, tool traces, fixed-pipeline comparison, and non-positive-value fallback assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Disable a failing parser tool and use the fixed extraction pipeline. Preserve malformed or unsupported cases in the failure ledger and never lower gold-case acceptance.

## Outputs

Versioned ExtractionAgent contracts, parser decisions, evidence-grounded records, tool trace, comparison metrics, failure ledger, focused tests, evidence report, and state/ledger advancement.
