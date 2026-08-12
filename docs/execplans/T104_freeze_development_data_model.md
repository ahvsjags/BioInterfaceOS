# T104 Freeze development data and model release

## Objective

Freeze the development data and model release after the Silver/Gold data
artifacts, modality links, uncertainty policy, multimodal model, and T102
robustness gate are complete. Emit a versioned release card with checksums for
all model-selection inputs, configurations, checkpoints, thresholds, and
dependencies, while preserving license-layer separation.

## Scope and constraints

- Verify T057 Silver, T062 modality links, T078 uncertainty, T079 multimodal,
  and T102 negative-control inputs by exact checksum and status.
- Include the existing immutable Gold-auto data release and its manifest without
  rebuilding or mutating it.
- Freeze model-selection inputs, configs, checkpoints, thresholds, and
  dependency metadata; do not expose locked targets or credentials.
- Remain offline and fixture-backed. No raw download, network, or provider-backed
  model execution is allowed.
- Never overwrite a prior data/model release. A changed input requires a new
  semantic version and a clean rerun of the robustness gate.

## Planned implementation

1. Inspect T057/T062/T078/T079 receipts, model cards, configs, and the existing
   Gold-auto manifest; define the development data/model release contract.
2. Add a freeze schema and sanitized fixture with pinned input checksums,
   dependency metadata, thresholds, license layers, and T102 status.
3. Implement a deterministic `release freeze-dev` workflow with public release
   card, model/data manifest, immutable receipts, and resume/tamper checks.
4. Add focused tests for checksum mutation, hidden-target isolation, license
   layer separation, version immutability, and resume determinism.
5. Run the complete lockfile, quality, data, benchmark, robustness, release,
   state, and diff gates, then record T104 and schedule T105/T106 as allowed.

## Acceptance criteria

- All required data/model inputs, configs, thresholds, dependencies, and
  checksums are frozen and reproducible.
- Data and model release cards are versioned, immutable, and license-layer
  separated.
- T102 strict negative controls remain clean and the existing immutable Gold-auto
  release verifies without mutation.
- Full repository, benchmark, and immutable-release gates pass.

## Failure fallback

Abort the freeze and retain the last clean release if any input is missing,
mutable, checksum-invalid, license-ambiguous, or robustness-invalid. Corrected
inputs receive a new release version; no prior release is overwritten.
