# T046: Build immutable Bronze data release

## Purpose

Assemble an immutable Bronze release from admitted raw and parsed assets, preserving raw payloads, provenance, license tiers, checksums, and exact rebuild receipts without normalization overwrite.

## Preconditions

T031, T032, T033, and T034 are DONE. Release freeze/verify and content-addressed asset checks are available.

## Non-goals

This task will not publish restricted payloads, bypass source policy, rewrite raw bytes, or merge normalized analytical records into the Bronze namespace.

## Interfaces and invariants

Every admitted raw or parsed asset must be represented by a manifest row with content hash, source locator, license tier, parser/schema version, and provenance. Release IDs and manifest hashes must be deterministic. Rebuilding the same fixture namespace must produce the same manifest and receipt bytes.

## Implementation plan

1. Inspect current manifest, asset, policy, and release interfaces.
2. Define a fixture-backed Bronze admission fixture with public, restricted-pointer, and parsed asset tiers.
3. Implement deterministic Bronze assembly and exact rebuild receipt generation.
4. Verify checksums, license-tier separation, raw-byte preservation, and restricted-payload pointer behavior.
5. Add the biointerfaceos data build-bronze command and focused tests.
6. Run the full acceptance gates and append evidence to the task ledger.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos data build-bronze --fixture
- biointerfaceos release verify --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- exact rebuild, checksum, license-tier, pointer-only, and raw-byte preservation assertions

## Failure recovery

Retain all source assets and receipts. If a manifest or receipt mismatch occurs, quarantine the candidate release and do not replace an existing immutable release.

## Outputs

Bronze release manifest, checksums, rebuild receipt, license-tier report, pointer registry, fixture/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
