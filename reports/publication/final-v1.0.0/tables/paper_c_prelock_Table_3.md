# Frozen analysis registry

| analysis | analysis_id | candidate_id | inputs | lockbox_rule | primary_metric |
| --- | --- | --- | --- | --- | --- |
| log-ratio functional-axis association | A1 | C1 | ['T090'] | recompute with frozen axis definition; abstain without axis support | bootstrap and leave-study stability |
| unit-aware symbolic expression evaluation | A2 | C2 | ['T093'] | evaluate the frozen expression; do not refit the selection rule | unit validity, nested study-CV, expression stability, OOD RMSE |
| protocol-adjusted boundary comparison | A3 | C3 | ['T094'] | repeat predefined protocol strata; retain counterexamples | raw versus adjusted effect and reversal tests |
| leave-material transfer validation | A4 | C4 | ['T092'] | score only supported overlap; preserve unmatched exclusions | held-out RMSE, overlap, calibration, abstention |
| supported counterfactual ranking | A5 | C5 | ['T095'] | score supported interventions only; no causal interpretation | rank stability and contradiction status |

All cells are rendered from checksummed source-data JSON; no manual edits.
