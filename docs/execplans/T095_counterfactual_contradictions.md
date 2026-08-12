# T095 Run counterfactual ranking and contradiction analyses

## Objective

Implement a deterministic, fixture-backed counterfactual ranking workflow that varies only supported interventions, checks positivity and OOD support, ranks outcomes under multiple predictive models, and explains contradictory evidence strata without silently resolving or deleting contradictions.

## Scope and constraints

- Consume T076 causal/predictive model audits, T089 frozen claim rules, T090 functional axes, T091 association-only mediation, T093 symbolic-law gates, and T094 protocol-boundary results.
- Freeze the intervention set, admissible ranges, positivity threshold, OOD threshold, ranking metric, model ensemble, contradiction taxonomy, and abstention rule before calculation.
- Generate counterfactual predictions only for supported interventions within observed material/protocol ranges; reject unsupported interventions and preserve them in an exclusion ledger.
- Compare rankings across at least two model families, quantify rank stability and uncertainty, and abstain when model disagreement or OOD distance exceeds the frozen gate.
- Build a contradiction graph over predefined evidence strata; report concordant, protocol-dependent, and unresolved contradictions with evidence links and no post-hoc deletion.
- Remain offline and fixture-backed; no network, credential, raw download, locked payload, or hidden target access.

## Planned implementation

1. Add `agents/discovery/counterfactuals.v1.json` for admissible interventions, positivity/OOD gates, model comparison, ranking uncertainty, contradiction taxonomy, and claim policy.
2. Add `tests/fixtures/omics/counterfactuals_fixture.json` with supported and unsupported interventions, model predictions, protocol strata, contradiction edges, and expected abstentions.
3. Implement `src/biointerfaceos/counterfactual_workflow.py` with intervention validation, positivity/OOD diagnostics, multi-model ranking, stability/uncertainty, abstention, contradiction graph construction, and evidence-linked reporting.
4. Expose `biointerfaceos discover counterfactuals --fixture` and emit preregistration, intervention audit, predictions, rankings, stability report, abstention ledger, contradiction graph/resolutions, language gate, lockbox scan, receipt, and manifest under `reports/omics/counterfactuals/`.
5. Add focused tests for supported-intervention restrictions, positivity/OOD checks, rank stability, abstention, contradiction preservation, resume determinism, and no hidden-target access.
6. Run focused tests, `UV_OFFLINE=1 make check`, and the complete dependency/assets/catalog/lockbox/release/state gate before recording T095.

## Acceptance criteria

- `COUNTERFACTUALS_VALID` reports only supported interventions and explicit exclusions.
- Positivity/OOD checks precede prediction; unsupported or unstable rankings abstain.
- At least two model families are compared with uncertainty and rank-stability metrics.
- Contradictory strata are preserved and categorized as resolved-by-protocol, model-disagreement, or unresolved.
- Resume output is deterministic and full repository/release gates pass.

## Failure fallback

Label unstable rankings as model-based hypotheses, exclude them from universal claims, and retain the contradiction graph with unresolved edges. Do not vary unsupported interventions or force a ranking.
