# T105 Draft Paper A benchmark manuscript

## Objective

Draft the benchmark manuscript from the frozen BioInterfaceBench development
release. Make every dataset, benchmark, grader, baseline, extraction, and
coverage statement traceable to immutable receipts and clearly separate
development-scope evidence from hidden-test or production claims.

## Scope and constraints

- Consume T103 frozen benchmark artifacts and T088 coverage/extraction reports;
  do not rebuild or alter frozen releases.
- Include benchmark construction, split/duplicate policy, graders, baselines,
  representation coverage, extraction performance, failures, abstentions, and
  limitations with exact receipt links/checksums.
- Do not include hidden target values, lockbox outcomes, unsupported causal
  claims, or production-scale generalization claims.
- Remain offline and use only repository-local artifacts. Preserve provenance for
  every table and figure input.
- Mark all claims as development-scope where the fixture or sample size limits
  external interpretation.

## Planned implementation

1. Inspect T088 coverage/extraction receipts and the T103 benchmark release card,
   manifest, grader, baseline, representation, and split artifacts.
2. Add a manuscript schema/fixture with a claim matrix, evidence locators,
   limitations, and table/figure source mappings.
3. Implement a deterministic `make paper-a` workflow that emits a manuscript
   draft, claim matrix, table data, figure manifest, and checksum receipt.
4. Add focused tests for frozen-input checksums, hidden-target exclusion, claim
   support, and resume determinism.
5. Run full quality, benchmark, robustness, release, state, compileall, and diff
   gates before recording T105.

## Acceptance criteria

- All benchmark numbers in the draft are generated from T103/T088 artifacts and
  have evidence-linked source paths and hashes.
- Public/hidden split remains intact; no hidden target or lockbox result is used.
- Failures, abstentions, coverage limits, and fixture-only scope are explicit.
- Draft, claim matrix, and receipt are byte-stable and immutable on resume.
- Full repository and immutable-release gates pass.

## Failure fallback

Block unsupported claims, retain the evidence gap in the claim matrix, and
regenerate only from corrected versioned inputs. Never edit a frozen release in
place.
