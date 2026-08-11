# T053: Implement raw mass-spec conversion workflow

## Purpose

Convert a bounded public/fixture RAW input to a vendor-neutral mzML representation, or explicitly bypass conversion for an already supported mzML input, while preserving checksums, instrument metadata, logs, and resumability.

## Preconditions

T052 is complete. The frozen PRIDE triage identifies one split-eligible development project and its public file/checksum metadata; restricted and locked projects remain excluded.

## Non-goals

This task will not access restricted or locked files, fabricate conversion success for unavailable vendor formats, or overwrite an existing verified conversion artifact.

## Interfaces and invariants

Every conversion receipt will capture source project/file identity, input checksum, output checksum, converter/version, instrument metadata, byte counts, status, and `resume_key`. A rerun with the same input and configuration is idempotent; mismatched checksums fail closed.

## Implementation plan

1. Define fixture RAW/mzML input and conversion-receipt schemas.
2. Implement a bounded converter or supported-mzML bypass with checksum and size gates.
3. Preserve instrument/project metadata and write deterministic logs and receipts.
4. Add resume/idempotency and refusal tests for restricted, oversized, and checksum-mismatched inputs.
5. Add `biointerfaceos omics convert --fixture` and focused tests.
6. Run the full offline gate, immutable release checks, and append evidence.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics convert --fixture`
- `biointerfaceos assets verify`
- `biointerfaceos lockbox self-test`
- `biointerfaceos state validate`
- `git diff --check`
- checksum, instrument metadata, resume, restriction, and size-gate assertions

## Failure recovery

Use the supported mzML bypass when available. If the vendor RAW is not safely convertible within the size/storage budget, preserve its metadata and classify it as unavailable for raw processing rather than downgrading the evidence silently.

## Outputs

Conversion artifacts, receipts, logs, focused tests, this ExecPlan, state advancement, and task-ledger evidence.
