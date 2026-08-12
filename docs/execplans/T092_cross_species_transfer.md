# T092 Model human-mouse and biofluid transfer

## Objective

Implement a deterministic, fixture-backed transfer workflow that compares direct, functional, optimal-transport, and conditional models for cross-species and cross-biofluid material transfer. The workflow must preserve pairing and material identity, report overlap limitations, validate on held-out materials, and abstain when transfer is unsupported.

## Scope and constraints

- Use the validated T056 material/corona module matrix, T078 uncertainty policy, T089 preregistration state, and T090 functional axes.
- Freeze the transfer estimand, source/target domains, material groups, feature representation, calibration metric, and abstention rule before fitting.
- Compare four declared methods: direct feature transfer, functional-axis transfer, bounded optimal transport, and conditional transfer with material covariates.
- Keep human/mouse and biofluid strata explicit; never pseudo-pair unmatched studies or merge samples across study/material identity.
- Perform leave-material-out validation with held-out target materials; expose overlap and positivity checks before scoring.
- Report calibration, ranking, transfer error, uncertainty, and abstentions. If overlap fails, return population-level functional comparison or abstain instead of inventing a transfer law.
- Run offline against a sanitized fixture only. No network, credential, raw download, locked payload, or hidden target access.

## Planned implementation

1. Add `agents/discovery/cross_species.v1.json` describing frozen methods, domains, overlap gates, pairing contract, validation, abstention, and artifact schemas.
2. Add `tests/fixtures/omics/cross_species_fixture.json` with human/mouse and biofluid rows, material IDs, functional axes, domain labels, calibration targets, held-out materials, and explicit unmatched cases.
3. Implement `src/biointerfaceos/cross_species_workflow.py` with deterministic direct/functional/OT/conditional baselines, material-group splits, overlap diagnostics, leave-material validation, calibration, ranking, and abstention.
4. Expose `biointerfaceos discover cross-species --fixture` and emit method comparison, overlap audit, pairing audit, leave-material report, calibration report, abstention ledger, lockbox scan, receipt, and manifest under `reports/omics/cross_species/`.
5. Add focused tests for no pseudo-pairing, frozen splits, method coverage, held-out material isolation, deterministic resume, overlap failure fallback, and abstention on unsupported domains.
6. Run focused tests, `UV_OFFLINE=1 make check`, and the full dependency/assets/catalog/lockbox/release/state gate before recording T092.

## Acceptance criteria

- `CROSS_SPECIES_VALID` reports all four transfer methods and both domain strata.
- Pairing is explicit, unmatched rows remain in an exclusion ledger, and no cross-study pseudo-pairs are created.
- Leave-material validation is separate from development fitting and contains no tuning on held-out materials.
- Overlap and calibration limitations are quantified; unsupported transfers abstain.
- A resume run is deterministic and target/lockbox/network gates remain clean.
- Full repository checks, immutable release verification, and state validation pass.

## Failure fallback

When overlap or pairing is insufficient, report a population-level functional comparison or abstain for that stratum. Do not claim individual-level transfer, alter material splits, or select a method after observing held-out targets.
