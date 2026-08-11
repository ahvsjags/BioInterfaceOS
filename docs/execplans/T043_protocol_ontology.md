# T043: Implement bioenvironment and protocol ontology

## Purpose

Normalize bioenvironment and experimental protocol fields into explicit ontology-backed entities, including serum/plasma/source, concentration, time, temperature, wash, centrifugation, assay, and replicate metadata while retaining missingness and severity features.

## Preconditions

T023, T039, and T040 are DONE. Ontology adapters, evidence locators, and unit normalization are available.

## Non-goals

This task will not impute missing protocol observations, turn unknown media into serum/plasma, or collapse incompatible protocol variants into one cluster.

## Interfaces and invariants

Each protocol field retains raw text, normalized entity/value when supported, unit-normalized quantity where applicable, exact source locator, confidence, and missingness status. Unknown fields remain explicit. Protocol clusters retain severity-relevant features and source provenance.

## Implementation plan

1. Define bioenvironment, protocol step, assay, replicate, missingness, and severity-feature schemas.
2. Build fixtures for serum/plasma/source, concentration, time, temperature, washes, centrifugation, assays, and replicates.
3. Implement ontology-backed value normalization using the committed unit registry and source adapters.
4. Preserve missing/unknown fields and mark unsupported or conflicting protocol values for review.
5. Build deterministic protocol clusters with severity feature vectors.
6. Add biointerfaceos resolve protocols --fixture, focused tests, and full acceptance gates.

## Progress

- [ ] Define protocol and bioenvironment schemas.
- [ ] Implement field normalization and missingness handling.
- [ ] Build protocol clusters and severity features.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos resolve protocols --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- source/media, concentration/time/temperature, wash/centrifugation, assay/replicate, missingness, and severity assertions

## Failure recovery

Keep raw protocol text and exact locators. Create unknown fields or protocol clusters with missing features; never impute unobserved steps.

## Outputs

bioenvironment/protocol registry, normalized protocol clusters, severity features, missingness/review queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
