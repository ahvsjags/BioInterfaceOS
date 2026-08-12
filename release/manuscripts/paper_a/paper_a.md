# BioInterfaceBench: Evidence-Bound Evaluation for Scientific Interface Benchmarks

## Abstract

BioInterfaceBench evaluates scientific-interface prediction as an evidence problem. The frozen development release contains 16 instances across 8 families, with 8 training and 8 validation instances. We separate public inputs from hidden-target metadata, compare 5 statistical baselines and 4 representation baselines, and retain extraction, coverage, and agent failures as first-class outputs. The best simple baseline reaches validation RMSE 0.409268; the best representation reaches 0.377238. Extraction accuracy is 0.500, while the high-confidence gate reaches precision 1.000 and recall 1.000. The dataset covers 7 independent studies, with 4 missing dimension values and 4 declared coverage gaps. These results define a reproducible development benchmark, not a production-scale estimate of scientific performance.

## 1. Introduction

Scientific interface studies combine materials, protocols, biological responses, and evidence locators. A benchmark can score predictions while hiding which records support each score. That design obscures extraction errors, split contamination, and missing study dimensions.

BioInterfaceBench uses an Evidence-Bound Benchmark Layer: every benchmark number links to a frozen input, a named metric, and a declared scope. The layer keeps public inputs separate from hidden-target metadata. It also preserves failed extraction rows, abstentions, coverage gaps, and negative controls beside successful results.

This paper makes three contributions:

1. **Benchmark contract.** We freeze 16 instances across 8 families under an 8/8 development split. The release records 3 grader cases and separates the public and hidden layers.
2. **Evidence comparison.** We compare five named statistical baselines, four representations, and an extraction gate. The comparison reports primary validation metrics, confidence intervals, missingness coverage, and failure categories.
3. **Scope accounting.** We quantify 7 independent studies, 4 missing dimension values, 4 coverage gaps, and seven scientific-agent tasks. The manuscript maps each claim to an immutable artifact.

## 2. The frozen benchmark boundary keeps evaluation auditable

The development release contains 16 instances, 8 families, and an 8/8 train/validation split. The release stores public instance inputs and a metadata-only hidden registry in separate files. Public records contain no target value, target hash, or hidden reference. Table 1 records the frozen composition.

The split uses paper-family group keys and retains missingness indicators. T102 negative controls pass strict mode with zero critical leakage. This boundary lets the benchmark report performance without reading hidden target payloads.

## 3. Evaluation setup

We evaluate three evidence layers. First, the extraction benchmark tests numeric, entity, arm, and evidence fields. Second, the prediction benchmark compares named baselines under the frozen split. Third, the agent benchmark measures completion, correctness, evidence grounding, schema validity, safety, reproducibility, and cost across seven tasks.

The primary prediction metric is validation RMSE on the held-out group. Each baseline records a confidence interval and a missingness policy. Representation results keep the full split as primary and report available-subset counts separately. Table 2 and Table 3 provide the complete baseline records.

## 4. Extraction errors define the first evaluation boundary

The extraction benchmark evaluates 8 rows and classifies 4 errors. Overall accuracy is 0.500. The high-confidence threshold is 0.85; it selects 4 rows with precision 1.000, recall 1.000, and calibration error 0.055. The G2 automatic-field gate passes.

The errors span numeric mismatch, entity resolution, arm labeling, and unresolved evidence locators. Figure 2 groups these outcomes by modality and shows why a single aggregate accuracy does not capture evidence quality.

**Takeaway.** The extraction gate supports automatic use only for the high-confidence subset. The full fixture remains a mixed-accuracy calibration benchmark.

## 5. Named baselines establish the prediction floor

The five statistical baselines define a prediction floor under identical splits. mean obtains the lowest validation RMSE at 0.409268; its confidence interval is [0.325000, 0.476314]. Table 2 reports every baseline rather than selecting a single favorable comparator.

The representation comparison separates descriptor, fingerprint, text, and polymer embedding inputs. fingerprint obtains the lowest representation RMSE at 0.377238. Structure-dependent representations report validation availability alongside the full-split metric. Figure 3 connects performance to coverage.

**Takeaway.** Fingerprint and descriptor results differ in both error and availability. The benchmark therefore treats representation coverage as part of model evaluation.

## 6. The agent suite measures execution quality beside prediction quality

The scientific-agent benchmark runs 7 tasks in no-tool, single-agent, and multi-agent modes. The selected mode is `single_agent`. Completion, correctness, evidence, schema, safety, and reproducibility each reach 1.000; the failure taxonomy remains explicit even when the aggregate failure count is 0.

The single-agent and multi-agent modes reach the same fixture quality metrics, while multi-agent coordination adds cost. Figure 4 reports this trade-off without treating coordination as a quality gain.

**Takeaway.** Agent execution metrics complement benchmark scores, but the fixture does not establish behavior on live scientific sources.

## 7. Coverage limits constrain every benchmark claim

The coverage audit counts 7 independent studies by stable study identifiers. It records 4 missing dimension values and 4 declared gaps. The warning ledger contains 9 warnings, and the audit performs no imputation. Table 4 lists the missing dimensions and Figure 5 maps the coverage gaps.

The observed studies cover only a subset of expected materials, endpoints, species, labs, and dates. One evidence row remains review-required. These patterns describe the fixture scope; they do not estimate literature prevalence.

**Takeaway.** Benchmark scores describe the frozen development scope. Broader claims require new study identity resolution, targeted search, and a new versioned release.

## 8. Limitations and reproducibility

This manuscript uses sanitized, fixture-backed artifacts. The benchmark contains 16 instances and 7 independent studies, so its estimates do not represent production-scale performance. The hidden layer remains metadata-only, and this draft uses no locked target values.

All tables, figures, and claims point to checksummed repository artifacts. A changed input requires a new benchmark version. The release card, claim matrix, and receipt preserve the exact evidence boundary used by this draft.

## 9. Conclusion

BioInterfaceBench turns benchmark evaluation into an evidence-linked workflow. The frozen release combines split isolation, named baselines, extraction gates, agent metrics, and coverage accounting. Its primary result is a bounded development benchmark whose numbers remain interpretable because the workflow records what the benchmark measures and where its evidence stops.

## Evidence references

The claim matrix maps labels E1--E8 to immutable repository artifacts and SHA-256 values. These internal evidence references support this development draft; external related-work citations remain a submission-stage addition.
