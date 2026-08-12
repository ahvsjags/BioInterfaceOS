# A bounded evidence workflow for multimodal scientific interface modeling

## Abstract

This method paper defines a reproducible workflow for scientific interface modeling. The development release contains 8 Silver tables and 3 admitted Gold-auto rows. It selects the conservative_conformal uncertainty policy and the material_protocol_masked multimodal representation. Five paired module ablations yield a mean full-minus-ablated effect of 0.081. Six outcome-independent dimensions produce 12 OOD group records, including 6 low-n groups. The OOD gate narrows the applicability domain. The method reports protected results only through checksummed metadata.

## 1. Method boundary

The workflow separates data, model, robustness, and manuscript layers. T104 freezes analysis-only data and model artifacts with redistributable configuration cards. The release contains no protected test values. Negative controls report zero critical leakage.

Every downstream result names its input artifact and its status. A changed input requires a new release or a rejected resume. This rule prevents a later manuscript from silently mixing data, model, and robustness versions.

**Takeaway.** The method is a release contract before it is a model description. The contract fixes what can support a method claim.

## 2. Frozen data and model layers

The frozen data layer contains 8 Silver tables and 3 Gold-auto rows. The model layer contains the conservative_conformal uncertainty model and the material_protocol_masked multimodal model. Six thresholds and four dependency entries are recorded in the release manifest.

The multimodal policy requires leakage control and missingness masks. The uncertainty policy abstains on two OOD cases in the upstream fixture. These policies are part of the method and are not post-hoc result filters.

## 3. Paired ablation design

We compare five essential modules under the same budget and frozen group splits. Each comparison contains four paired units and budget eight. The effect is the full metric minus the ablated metric. The mean effect across modules is 0.081.

The largest paired effect is 0.110 for the candidate_audit_support module. Its calibration gain is 0.060. Its OOD RMSE gain is 0.115. These values describe the fixture and do not establish independent causal effects.

One non-essential provider-backed raw-data ablation is interface-blocked. The missingness ledger records that block. The claim gate reports zero blocked essential claims.

**Takeaway.** The ablation design supports a bounded module comparison. It does not support a causal decomposition beyond the paired fixture contract.

## 4. Calibration and OOD handling

The method records calibration and OOD changes for every essential ablation. It keeps calibration gains separate from primary prediction metrics. This separation prevents a calibration improvement from being presented as a prediction improvement.

OOD groups use outcome-independent keys for study, lab, family, species, biofluid, and time. The primary suite contains 12 group records. Six groups are low-n and receive abstention flags. The claim status is `NARROWED_BY_OOD`.

The largest-study exclusion, low-n exclusion, and evidence-grade-only scenarios produce 3 sensitivity records. Their primary metrics are retained as scenario evidence rather than pooled into a single estimate.

**Takeaway.** Applicability is restricted to groups with sufficient support. Low-n and OOD records remain visible and are not silently pooled.

## 5. Agent evaluation as a method check

The upstream scientific-agent suite covers 7 tasks and 3 modes. It selects `single_agent`. Completion, correctness, evidence, schema, safety, and reproducibility each equal 1.000 in the fixture. The failure taxonomy remains part of the evidence package.

Agent evaluation tests workflow execution and evidence handling. It does not establish model performance on live sources. Coordination cost and external-source behavior require a separate study.

## 6. Reproducibility and claim controls

The method stores schemas, fixtures, receipts, manifests, tables, and figure specifications. First generation and resume compare bytes. Checksum mutation and artifact tampering raise errors. The full project gate runs offline.

The claim matrix marks each statement as supported development scope, narrowed by OOD, or limitation required. The manuscript does not promote blocked modules, protected results, or unsupported causal language.

## 7. Limitations

The release is fixture-backed and development-scoped. Its data and model artifacts are analysis-only. The OOD groups are small, and the applicability claim is narrowed. The ablation comparison uses paired fixture units rather than a production campaign.

The agent suite does not test live-source behavior. The non-essential raw-data ablation remains interface-blocked. External citations and venue-specific formatting remain submission-stage work.

## 8. Conclusion

The method combines immutable release boundaries, explicit uncertainty, paired ablations, OOD abstention, and agent evidence. Its strongest result is a reproducible workflow with visible failure and applicability limits. Future releases may extend the evidence domain only after new inputs pass the same contract.

## Evidence references

The claim matrix maps method statements to the T104, T088, T099, and T100 artifacts and their SHA-256 values. The receipt records the exact input set and manuscript bytes.
