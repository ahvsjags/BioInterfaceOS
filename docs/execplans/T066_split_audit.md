# T066 adversarial leakage and lockbox audit

## Purpose

Audit the frozen T065 development split against identity leakage, study-only and ID-hash attacks, path/layout/source features, duplicate contamination, and the lockbox firewall before benchmark construction.

## Preconditions

T065 frozen split manifest and feature blacklist are complete. T015 lockbox policy and the development path guard are available. No locked payload may be opened during this audit.

## Non-goals

This task will not inspect hidden labels, unlock the lockbox, change split assignments after seeing outcomes, or train a predictive model on the development data.

## Interfaces and invariants

The audit receives frozen split/hash inputs and injected attack fixtures. Every attack records feature name, expected detection, observed result, severity, and remediation. Mandatory identity/path/layout attacks must fail or be blocked; critical findings are zero before approval.

## Implementation plan

1. Hash and load T065 split/blacklist/leakage artifacts and T015 lockbox policy.
2. Define injected identity, accession, author, journal, layout, path, study-only, ID-hash, duplicate, and forbidden-lockbox attack cases.
3. Run blacklist detection, group/duplicate containment, study-only and ID-hash sensitivity checks, and lockbox forbidden-read test.
4. Emit attack findings, contamination scan, approval receipt, deterministic receipt/log/manifest, tests, evidence, and state advancement.
5. Add `biointerfaceos split audit --strict`.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos split audit --strict`
- all mandatory leakage attacks detected/blocked and critical findings zero
- lockbox forbidden read remains blocked; split hashes unchanged
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Any critical leakage or lockbox finding invalidates the split approval. Preserve the attack receipt, remove the affected feature/path from the development interface, rebuild T065, and rerun the complete audit.

## Outputs

Leakage attack findings, contamination scan, approval receipt, deterministic receipts/logs/manifests, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
