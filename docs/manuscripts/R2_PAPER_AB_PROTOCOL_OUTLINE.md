# BioInterfaceOS: auditable provenance and source-locator benchmark protocol for biointerface evidence

## Scope and status

This is the merged R2 A+B protocol outline. It is **not submission-ready**.
It replaces neither a real biological prediction study nor an empirical causal
model. Its currently supportable contribution is an auditable source-provenance
and raw-cell locator workflow on openly accessible observations. The historical
fixture manuscripts are withdrawn from R2 submission scope.

## Research question and contribution

The protocol asks how a biointerface evidence workflow can preserve source,
study, laboratory, material, biological system, protocol, outcome, unit and
cell-level locator information while preventing fixture outputs from being
misrepresented as empirical validation. The intended manuscript has one
non-overlapping contribution: provenance-aware benchmark design plus a strict
source-locator baseline and its limitations.

## Real-data provenance and source-locator task

Describe T120's source admission and T122's study-held-out locator task using
only their receipts and raw prediction archive. A locator resolves a declared
source value; it does not establish a biological effect, claim verification or
model utility. Retain source-defined independent units and declare any missing
unit as `source_not_stated` rather than inferring comparability.

## Benchmark design and statistical boundary

State the frozen estimand, group hierarchy, split construction, calibration,
coverage, cluster-aware uncertainty and missingness policy from T121--T122.
Explain that the current three endpoints are heterogeneous and that T123 found
zero compatible cross-study targets. No model effect, paired ablation,
generalisation or external OOD result belongs in this version.

## Related work and comparator boundary

Use the externally verified comparator map: MIRIBEL and MINBE for reporting,
eNanoMapper for structured terminology, SciFact for the distinction between
locating evidence and assessing a claim, WILDS for declared distribution shift,
and life-science ML reproducibility guidance for artifact disclosure. Cite the
full verified R2 reference packet; do not repurpose any comparator result as a
BioInterfaceOS score.

## Results available now

Report only source admission, source-locator resolution, coverage and
calibration artifacts at their declared development-observation scope. Show
the evidence-boundary and public-release protocol figures; they render no
empirical values. State that 15 historical fixture-derived figure panels were
withdrawn from R2 submission scope.

## Results withheld pending T123

Training, paired ablations, negative controls and OOD reporting are withheld
until at least three laboratories contribute a source-defined identical target,
unit and biological-condition protocol. This is a data-admission requirement,
not a negative or positive model result.

## Figures, data, code and availability

Use only R2 Figures 1--3 with their source cards and QA receipt. Provide the
controlled source registry, checksums, code, environment lock and public
software replay receipt with explicit boundaries. Do not present a software
replay as scientific reproduction.

## Limitations and transition criteria

The A+B manuscript may move from protocol to a real-data benchmark/method
manuscript only after T123 passes its compatible-target, paired-run,
negative-control and declared OOD gates. A subsequent independent evaluator
and external reproduction remain separate requirements for stronger claims.
