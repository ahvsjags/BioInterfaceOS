# T079 Multimodal material and document representations

## Purpose

Compare material, protocol, structure, figure, and text representations with a leakage-safe multimodal fusion model. Missing-modality masks and OOD persistence must be explicit, and article text must not contain outcome-derived information.

## Preconditions

T070 representation baselines, T074 compositional modeling, and T078 uncertainty/abstention are valid. The multimodal fixture must preserve source provenance and distinguish material/protocol metadata from article outcome text.

## Non-goals

This task will not use source identity as a shortcut, include outcome-bearing article text, impute unavailable modalities without a mask, or accept a fusion gain that disappears on OOD rows.

## Interfaces and invariants

`biointerfaceos train multimodal --config configs/models/multimodal.yaml` will compare each modality with fusion, emit missing-modality masks and source-identity leakage audits, and require fusion gains to persist on OOD rows. Outcome-contaminated text is removed and material/protocol-only representations are retained.

## Implementation plan

1. Define sanitized modality records with provenance, masks, domain labels, and OOD flags.
2. Fit text, structure, figure, material/protocol, and multimodal fusion baselines under one budget.
3. Audit source identity and outcome-text leakage, then evaluate missing-modality variants.
4. Compare in-domain and OOD gains; select a masked conservative fusion fallback if gains do not persist.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train multimodal --config configs/models/multimodal.yaml`
- fusion-vs-single-modality, missing-modality masks, source-identity leakage, and OOD persistence assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If fusion gains do not persist OOD or leakage is detected, remove outcome-contaminated text and retain material/protocol-only masked representations. Record the failure and abstain on unsupported modalities.

## Outputs

Versioned multimodal config, modality audit, leakage audit, missingness report, model comparison, OOD evaluation, focused tests, evidence report, and state/ledger advancement.
