# T112 Build reproducibility containers and clean-room package

## Objective

Create a clean-room reproduction workflow and license-safe public package from
the committed code, lockfiles, frozen release metadata, sealed lockbox metadata,
and final publication package. The workflow must not download protected data or
models, must support network-free benchmark grading, and must emit three
independent reproduction receipts.

## Scope

- Validate the frozen environment and dependency lock without network access.
- Build a redistributable package containing code, schemas, fixtures, manifests,
  metadata-only results, final figures/tables, and source-data licenses.
- Exclude lockbox payloads, credentials, protected raw values, and non-licensed
  source data.
- Run the deterministic public benchmark/reproduction workflow three times in
  isolated output directories and compare receipts byte-for-byte.
- Record dependency/environment drift and exact nonredistributable rebuild steps.

## Implementation steps

1. Add a versioned clean-room schema and fixture with explicit include/exclude
   rules and license checks.
2. Implement `reproduce-clean --strict` with network denial, lockfile checks,
   package manifest generation, deterministic benchmark execution, and three
   receipts.
3. Add focused tests for forbidden files, license gaps, network attempts,
   receipt divergence, and protected-value contamination.
4. Add the CLI command and `make reproduce-clean` target.
5. Generate and verify the public package and three independent receipts.
6. Record T112 and activate T113 only after the package is audit-complete.

## Acceptance criteria

- Clean-room rebuild works from the committed repository and frozen lockfile.
- Network-free benchmark grading passes.
- Three independent receipts agree on package and result hashes.
- Public package is license-safe and contains no protected raw values, lockbox
  payloads, credentials, or models.
- Reproduction command and exact unmet/nonredistributable steps are documented.

## Fallback

Quarantine any file with unknown provenance or license status. Publish only the
metadata-only and reproducible subset, and document exact external rebuild steps
instead of copying nonredistributable data.
