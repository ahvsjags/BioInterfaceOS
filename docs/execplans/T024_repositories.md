# T024: Implement public repository/code asset adapters

## Purpose

Add policy-gated metadata adapters for Zenodo, Figshare, OSF, and public GitHub releases so reproducible code/data pointers can be recorded without executing ingested code or requiring user credentials.

## Preconditions

T016 and T023 are DONE. The anonymous network client, source policy engine, source manifest, content-addressed store, and append-only provenance ledgers are available.

## Non-goals

This task will not clone or execute arbitrary repositories, use personal access tokens, infer licenses from prose, or promote assets with ambiguous redistribution terms.

## Interfaces and invariants

Each candidate must retain repository/provider, DOI or release identifier, commit/tag, version/date, license, download URLs, access requirements, response hash, and provenance evidence. Public metadata may be retained when an asset is rate-limited or license-ambiguous; such records are not admitted for redistribution until the policy engine passes them.

## Implementation plan

1. Define provider-specific anonymous metadata endpoints and bounded pagination for Zenodo, Figshare, OSF, and GitHub public releases.
2. Normalize DOI/release/commit/license metadata through the source adapter contract.
3. Add sanitized fixtures covering public releases, missing licenses, pagination, rate limiting, and duplicate URLs.
4. Enforce policy before metadata/assets access and explicitly reject credential-required or unclear-license cases.
5. Add a dry-run source command and run focused/full offline gates, compileall, release, catalog, lockbox, state, and diff checks.
6. Record append-only evidence, advance the task graph, and commit.

## Progress

- [x] Read and pin official provider endpoint contracts.
- [x] Implement and test the repository adapters.
- [x] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- .venv/bin/biointerfaceos repository sync --dry-run
- .venv/bin/pytest -q tests/sources/test_repositories.py
- .venv/bin/python -m compileall -q src tests
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos catalog check
- biointerfaceos state validate
- git diff --check
- public-release metadata, DOI, commit/tag, license, pagination, rate-limit retry, duplicate URL, policy quarantine, and no-code-execution assertions

## Failure recovery

If a provider rate-limits or transiently fails, retain the bounded query receipt and metadata pointer, back off according to the network client, and leave binary fetching disabled until an admitted public release is verified.

## Outputs

src/biointerfaceos/sources/repositories.py, tests/sources/test_repositories.py, tests/fixtures/sources/repositories, this ExecPlan, reports/T024_repositories.md, state advancement, and task-ledger evidence.

## Completion note

T024 completed with implementation commit 4a438421d4de44fc68acf07e08cfa0e94b6ec2fc. Final acceptance evidence is recorded in reports/T024_repositories.md.
