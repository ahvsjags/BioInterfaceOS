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

## Completion evidence

- Implementation commits: `1cb06b3` (bounded conversion workflow) and `587fd3b` (checksum refusal fixture and regression coverage).
- Fixture conversion result: 5 input records; 1 completed supported-mzML bypass and 4 explicit refusals (`REFUSED_RESTRICTED`, `REFUSED_SIZE`, `REFUSED_UNSUPPORTED_FORMAT`, and `REFUSED_CHECKSUM`).
- The completed record preserved `Orbitrap Fusion` metadata, 171 input/output bytes, identical input/output SHA-256 `556f2768a34cdbc53e8db91feff6877634b60719f006d67e892d12cba5e7424f`, and resume key `df3bceaf5df6d88698c5c1d96f2d5520e77ff5fc44f30fd066522f7e04e6e2c7`.
- A second identical run resumed the existing artifact (`resumed=1`) without changing receipt bytes. No raw payload was downloaded and no locked payload was accessed.
- Focused conversion/PRIDE tests: 5 passed. Full offline gate: 202 tests passed; Ruff, format, mypy, UV lock/sync, data validation, review export, assets, catalog, lockbox, release, state validation, compileall, and `git diff --check` passed.
- Deterministic artifacts: `reports/omics/conversion/conversion_manifest.json` (`18929567250fe5edee2b5bbf076bec257399736f58a2dd1a2d5d9b4a0a03d1dc`), `reports/omics/conversion/conversion_log.json` (`78552fcea8ffc9e8b629a9880b7660ea5f49b6b71cfb1c429bc2123e00670802`), `reports/omics/conversion/conversion_receipt.json` (`2c58c5921b2bfc09d36448ce94e851598ab0e350d6807c8e8b4b2309c9fb211f`), and `reports/omics/conversion/artifacts/PXD000001.mzML` (`556f2768a34cdbc53e8db91feff6877634b60719f006d67e892d12cba5e7424f`).
