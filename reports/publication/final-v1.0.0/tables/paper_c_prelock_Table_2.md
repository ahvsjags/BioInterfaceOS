# Predicted lockbox outcomes

| abstain_if | candidate_id | expected | prediction_id | status | postlock_status | abstained | failure_class |
| --- | --- | --- | --- | --- | --- | --- | --- |
| functional axes are unavailable or the evaluated group is OOD | C1 | association direction remains within the frozen development envelope | P1 | PREDICTED_BEFORE_LOCKBOX | POSTLOCK_REPLICATED | False | none |
| units fail, expression support is OOD, or stability falls below the frozen gate | C2 | the frozen expression remains unit-valid on supported cases | P2 | PREDICTED_BEFORE_LOCKBOX | POSTLOCK_REPLICATED | False | none |
| protocol variables or comparable-study strata are unavailable | C3 | protocol adjustment remains boundary-dependent rather than universal | P3 | PREDICTED_BEFORE_LOCKBOX | POSTLOCK_INCONCLUSIVE | True | protocol_boundary |
| material overlap or leave-material support fails | C4 | transfer is supported only where material overlap passes | P4 | PREDICTED_BEFORE_LOCKBOX | POSTLOCK_REFUTED | False | overlap_failure |
| positivity, OOD, or model agreement fails | C5 | supported rankings remain stable only after positivity and model-agreement checks | P5 | PREDICTED_BEFORE_LOCKBOX | POSTLOCK_INCONCLUSIVE | True | model_disagreement |

All cells are rendered from checksummed source-data JSON; no manual edits.
