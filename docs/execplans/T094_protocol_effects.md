# T094 Test protocol-correction and reversal hypotheses

## Objective

Implement a deterministic, fixture-backed protocol-effects workflow that tests whether protocol variables explain, correct, or reverse material–corona–outcome associations. The workflow must use predefined protocol variables, comparable-study/within-study contrasts, Simpson/reversal diagnostics, and a claim gate that prevents universal reversal wording.

## Scope and constraints

- Use validated T071 model results, T089 frozen claim rules, and T091 mediation evidence; preserve the association-only language status where causal identification is absent.
- Freeze the protocol ontology, correction variables, contrast definitions, reversal thresholds, subgroup policy, and claim wording before fitting.
- Compare raw effects with protocol-adjusted effects within comparable studies and across study strata; report heterogeneity and sign changes.
- Run Simpson/reversal tests using predefined study, species, biofluid, assay, and dose/protocol strata. No post-hoc subgroup search or cherry-picking.
- Keep all exclusions explicit, retain counterexamples/adverse strata, and downgrade to protocol dependence/boundary effects when reversal is unstable.
- Remain offline and fixture-backed; no network, credential, raw download, locked payload, or hidden target access.

## Planned implementation

1. Add `agents/discovery/protocol_effects.v1.json` for protocol ontology, contrasts, reversal tests, subgroup policy, heterogeneity, and language gate.
2. Add `tests/fixtures/omics/protocol_effects_fixture.json` with study-preserving material/intervention rows, predefined protocol variables, raw/adjusted outcomes, and reversal/counterexample strata.
3. Implement `src/biointerfaceos/protocol_effects_workflow.py` with within-study contrasts, protocol correction, comparable-study pooling, Simpson diagnostics, reversal stability, heterogeneity, and claim gating.
4. Expose `biointerfaceos discover protocol-effects --fixture` and emit preregistration, ontology audit, raw/adjusted effects, heterogeneity map, reversal tests, exclusion ledger, language gate, lockbox scan, receipt, and manifest under `reports/omics/protocol_effects/`.
5. Add focused tests for predefined-variable enforcement, no post-hoc subgroup selection, sign-change detection, counterexample retention, resume determinism, and protocol-dependence wording.
6. Run focused tests, `UV_OFFLINE=1 make check`, and the complete dependency/assets/catalog/lockbox/release/state gate before recording T094.

## Acceptance criteria

- `PROTOCOL_EFFECTS_VALID` reports raw and adjusted effects for all predefined protocol variables.
- Within/comparable-study analyses and Simpson/reversal tests are explicit and study-preserving.
- Heterogeneity and counterexamples are retained; no post-hoc subgroup cherry-picking is possible.
- Claim wording is universal only if reversal is stable and all gates pass; otherwise it is protocol-dependent/boundary wording.
- Resume output is deterministic and full repository/release gates pass.

## Failure fallback

If reversal is unstable or protocol correction cannot be identified, report protocol dependence and boundary conditions. Do not publish universal reversal or causal correction claims.
