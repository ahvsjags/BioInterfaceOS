# T103 Freeze BioInterfaceBench development release

## Objective

Freeze the development BioInterfaceBench release after all benchmark instances,
graders, statistical/representation baselines, and negative-control audits are
complete. Produce an immutable versioned benchmark manifest and card with
checksums, while keeping public and hidden layers separated.

## Scope and constraints

- Consume the completed T067-T070 benchmark artifacts and T102 negative-control
  gate as frozen inputs.
- Preserve the existing public/hidden split boundary and never read or expose
  locked test payloads or target values.
- Freeze instance, grader, split, baseline receipt, and benchmark-card hashes in
  one versioned manifest; do not overwrite any prior release.
- Remain offline and fixture-backed. No raw download, network, credentials, or
  provider-backed benchmark execution is allowed.
- Refuse to freeze if any prerequisite checksum, schema, state, lockbox, or
  negative-control gate is invalid.

## Planned implementation

1. Inspect existing benchmark instance, grader, baseline, representation, split,
   and robustness receipts and define the versioned development-release contract.
2. Add a freeze schema/fixture and a deterministic workflow that verifies all
   prerequisite hashes, public-hidden separation, grader coverage, and clean
   negative-control status before writing a new release directory.
3. Expose `biointerfaceos benchmark freeze-dev` with resumable, byte-stable
   manifest and benchmark-card outputs.
4. Add focused tests for prerequisite checksum failure, hidden-layer isolation,
   immutable versioning, and resume determinism.
5. Run the full lockfile, quality, data, release, state, and diff gates, then
   record T103 and unblock T104/T105 only when their dependencies are satisfied.

## Acceptance criteria

- Instance, grader, split, and baseline/representation receipt hashes are
  immutable and recorded in a versioned benchmark release.
- Public and hidden layers remain separated; no hidden target value appears in
  release artifacts.
- Benchmark card, manifest, and receipt reproduce byte-for-byte on resume.
- T102 strict negative-control gate remains `ATTACKS_CLEAN`.
- Full repository and immutable data-release gates pass.

## Failure fallback

Abort the freeze and retain the previous clean release if any prerequisite is
missing, mutable, checksum-invalid, or leaks hidden data. Create a new release
version for corrected inputs; never overwrite a prior release.
