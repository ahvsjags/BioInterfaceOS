# T114 Run final project acceptance and release

## Objective

Run the final project acceptance across mandatory task states, repository gates,
release signatures, clean-room reproduction, lockbox boundaries, publication
artifacts, claim audit, and public-package license safety. Produce
`reports/FINAL_AUDIT.md`, a final checksum index, and a versioned public release
without marking the project complete while any critical gate remains unmet.

## Acceptance gates

- G0 task/state/ledger consistency and immutable history.
- G1 dependency lock, environment, formatting, lint, typing, tests, compileall.
- G2 schema, fixture, asset, catalog, and checksum validation.
- G3 immutable dev/pre-lock release and signature verification.
- G4 lockbox firewall, one-shot evaluation, audit transitions, no raw values.
- G5 final figures/tables: 15 figures, 18 tables, source-data mappings, 600-dpi
  raster/vector outputs, and receipt verification.
- G6 clean-room package: license-safe allowlist, three agreeing offline receipts,
  no locked/raw/CAS/credential/model payloads.
- G7 final claim/language audit: 24 claims, 246 sentences, zero blockers.
- G8 public release manifest, checksums, provenance, and archive verification.
- G9 explicit limitations and nonredistributable rebuild instructions.
- G10 final git status, tag candidate, and reproducibility handoff.

## Implementation steps

1. Add the versioned acceptance schema and fixture.
2. Implement `project accept --strict` to run all gates, collect evidence hashes,
   and refuse release on any critical failure or dirty untracked artifact.
3. Generate `reports/FINAL_AUDIT.md`, `release/public/bioif-public-v1.0.0/`,
   `final_checksums.sha256`, and a release receipt.
4. Add focused tests for missing task evidence, stale receipts, checksum drift,
   dirty public files, and unmet external-citation limitations.
5. Run the full suite and verify the public release archive.
6. Record T114 and report any remaining noncritical submission-stage limitation.

## Acceptance criteria

- All mandatory tasks T000-T114 are DONE or explicitly recorded as WAIVED.
- Critical findings are zero; public package and checksums verify.
- The project remains `IN_PROGRESS` until the user explicitly accepts final
  publication/completion; no fabricated completion status is emitted.
- Public release contains only license-safe, metadata-only, reproducible outputs.

## Fallback

Do not mark COMPLETE if any gate fails. Publish the validated partial release,
record exact unmet gates and responsible artifacts, and leave the project state
IN_PROGRESS with a reproducible remediation plan.
