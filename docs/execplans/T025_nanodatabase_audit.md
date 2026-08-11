# T025: Audit specialized nanomaterial databases

## Purpose

Audit candidate nanomaterial databases for anonymous access, license clarity, exportability, schema usefulness, and suitability for later BioInterfaceOS discovery. Produce admission decisions before any adapter or data fetch is queued.

## Preconditions

T011, T016, T023, and T024 are DONE. The policy engine, anonymous network client, source manifest, repository/ontology adapters, and append-only evidence ledgers are available.

## Non-goals

This task will not use credentials, scrape protected portals, download large scientific assets, infer redistribution rights, or make a rejected database a project blocker.

## Interfaces and invariants

Every candidate receives a decision record with provider URL, anonymous-access evidence, API/export route, license signal, schema/data relevance, duplicate/provenance risks, policy outcome, and recommended follow-up. Unknown or credentialed access is rejected or quarantined; only admitted candidates may be queued for adapters.

## Candidate set

The initial audit will cover NanoCommons Knowledge Base, eNanoMapper/nanomaterial registry services, Nanomaterial-Biological Interactions Knowledgebase candidates, PubChem/ChEMBL as already-admitted substitutes, and public supplementary nanomaterial repositories reachable through Zenodo/Figshare/OSF. Candidate names are hypotheses until endpoint and license evidence is recorded.

## Implementation plan

1. Inspect official landing pages and public API/export documentation for each candidate.
2. Record anonymous-access, registration/login, rate-limit, license, exportability, schema, and provenance evidence.
3. Run policy decisions on sanitized candidate records; separate admitted, metadata-only, quarantined, and rejected sources.
4. Compare candidate fields against BioInterfaceOS material, corona, endpoint, and protocol schemas.
5. Write reports/NANODATABASE_ADMISSION.md and sanitized audit fixtures/tests.
6. Run offline/full gates, compileall, source policy, catalog, state, lockbox, release, and diff checks.
7. Record append-only evidence and advance the task graph only when all candidate decisions are auditable.

## Progress

- [ ] Read and pin official candidate endpoint and license contracts.
- [ ] Complete anonymous-access and schema audit.
- [ ] Write admission report and run acceptance gates.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos source policy self-test
- biointerfaceos catalog check
- biointerfaceos state validate
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- git diff --check

## Failure recovery

If a candidate is unavailable or unclear, preserve the exact evidence URL and classify it as metadata-only, quarantined, or rejected; continue with the admitted public substitutes and do not use credentials.

## Outputs

reports/NANODATABASE_ADMISSION.md, audit fixtures/tests, this ExecPlan, state advancement, and task-ledger evidence.
