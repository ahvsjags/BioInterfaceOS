# T031: Implement policy-gated asset downloader

## Purpose

Fetch only policy-admitted public fixture assets into the content-addressed asset store, verify content type, size, and SHA-256 before promotion, preserve provenance receipts, support safe resume, and quarantine failures.

## Preconditions

T012, T018, and T030 are DONE. Source policy, network client, manifest registry, asset store, paper-family outputs, and lockbox firewall are available.

## Non-goals

This task will not fetch locked-test payloads, execute downloaded code, bypass policy decisions, or promote assets with missing or conflicting hashes.

## Interfaces and invariants

Every queue item includes source identity, URL, expected SHA-256, expected content type, maximum size, policy decision, and lockbox flag. Only ADMIT_PUBLIC_REDISTRIBUTABLE items may enter the asset store. Download bytes are streamed with a size limit, content type and hash are verified before atomic promotion, and failed items enter quarantine with a reason. Existing valid CAS blobs are resumable and do not duplicate.

## Implementation plan

1. Define download queue, receipt, quarantine, and fixture payload schemas.
2. Implement policy gate before network access and lockbox path/field firewall checks.
3. Stream fixture assets into temporary files with content-type, size, and hash verification.
4. Atomically promote verified bytes to the CAS and register manifest provenance.
5. Add fixture CLI command biointerfaceos data fetch --fixture and assets verification tests.
6. Run full gates, validate asset receipts/manifests, and record evidence.

## Progress

- [ ] Define download queue and asset receipt schemas.
- [ ] Implement gated streaming download, resume, verification, and quarantine.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos data fetch --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos state validate
- git diff --check
- content-type/size/hash and resume assertions
- append-only receipt and manifest validation

## Failure recovery

Keep partial temporary downloads out of the CAS. Quarantine mismatched bytes with the reason and response hash; retry only the affected admitted queue item. Never rewrite prior receipts or delete failed evidence.

## Outputs

download queue, asset receipts, CAS assets, updated source manifest, quarantine records, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
