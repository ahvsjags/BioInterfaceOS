# R4-T280 paper-data primary-route decision — 2026-08-15

## Decision

The manuscript primary paper-data analysis is now fixed to **T195**, not T277. T195 is the cleanest route for the data-foundation claim because it uses three separately anchored, legally redistributable public source packages and an exact nine-target intersection frozen before model execution.

| Route | Role | Labs | Targets | Main accounting | Why it is not pooled with the others |
|---|---|---:|---:|---|---|
| T195/T192 | Primary redistributable portability | 3 | 9 | 809 observations, 85 batches | Dalian is pooled/unspecified; Edinburgh donor IDs are not encoded |
| T265 | Biological-unit sensitivity | 3 | 5 | 3,853 observations, 246 units, 916 batches | Includes analysis-only/non-redistributable source assets |
| T193 | Target-rich sensitivity | 3 | 99 | 1,495 observations, 85 batches | Different source lineage and target universe |
| T277 | Technical-replicate-aware sensitivity | 4 | 7 | 783 raw, 671 fit, 112 collapsed groups, 115 batches | Different source panel and replicate estimand |

## What this solves

This resolves the manuscript-level ambiguity about which paper-derived route supports the claim “three independently anchored laboratories share a pre-frozen, row-traceable target.” The T195 route has explicit CC-BY/CC0 redistribution boundaries, source maps, source coordinates, finite-positive rank rules, leave-one-laboratory-anchor-out evaluation, nested batch selection, cluster bootstrap, paired ablation and within-batch permutation controls.

The paper/full-text route therefore supplies genuine published experimental observations for an author-side computational benchmark. It does not become a new experiment, and it does not create a non-author evaluator, an independent no-author reproduction or community adoption.

## Manuscript claim boundary

The primary claim should be phrased as exploratory cross-laboratory portability of within-batch protein-quantification rank from sequence features. It must not claim absolute cross-study abundance, donor-level replication from laboratory count, material-design efficacy, clinical utility or independent validation. The negative and zero incremental ablation results remain part of the result, not grounds for route switching.

## Remaining strong-Q1 gates

The route decision improves the scientific evidence hierarchy but leaves the hard gates unchanged: one real protected lockbox receipt, one genuine no-author accession-to-result reproduction, two distinct external-user records, authenticated DOI manifest/archive read-back and final multi-agent editorial review are still required. `scientific_submission_ready=false` remains mandatory.
