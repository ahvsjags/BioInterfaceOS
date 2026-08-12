# T105 Draft Paper A benchmark manuscript

## Result

T105 was completed on the KAUST Ibex server at implementation commit `be248f3`.
The workflow creates an evidence-linked Paper A manuscript from the frozen
`biointerfacebench-dev-v1.0.0` release. It records the benchmark boundary,
split and family structure, baseline and representation comparisons,
extraction quality, agent-mode comparison, coverage gaps, limitations, and
reproducibility metadata without accessing protected target values.

## Reproducible command

```bash
make paper-a
```

Observed first run:

```text
PAPER_A_VALID release_id=biointerfacebench-dev-v1.0.0 instances=16 families=8 train=8 validation=8 claims=8 tables=6 figures=5 evidence_inputs=18 style_passed=true resumed=0 target_values_exposed=false
```

The second run resumed byte-stably. The focused manuscript suite passed 3/3
tests, including input-checksum rejection and tamper rejection.

## Evidence boundary

The manuscript is grounded in 18 checksum-pinned inputs: the frozen benchmark
manifest and card, processing/grading/baseline/representation receipts and
results, extraction and coverage reports, agent receipts and mode comparison,
and the upstream T050/T051/T088 reports. It uses the public development
metadata and reported validation metrics only. No hidden target payload,
locked test result, external download, credential, or network resource was
accessed.

## Main reported results

| Component | Result |
|---|---|
| Frozen benchmark | 16 instances, 8 families, 8 train, 8 validation, 3 grader cases |
| Simple baselines | Five named baselines; mean RMSE 0.409268 on 8 validation instances |
| Representations | Fingerprint RMSE 0.377238 with 0.375 coverage; text RMSE 0.412300 with full coverage |
| Extraction | 8 rows, accuracy 0.500000, eligible precision 1.000000, eligible recall 1.000000, G2 PASS |
| Coverage | Seven independent studies represented; missingness retained and no imputation applied |
| Agent suite | Seven tasks; single-agent mode selected; completion, correctness, evidence, schema, safety, and reproducibility all 1.0 |

## Acceptance evidence

| Gate | Result |
|---|---|
| Full test suite | 346 passed |
| Lock and environment | `uv lock --check` and frozen `uv sync` passed |
| Static checks | ruff check, ruff format check, mypy, compileall, and `git diff --check` passed |
| Repository checks | Schema, assets, catalog, lockbox, immutable release, and project state passed |
| Manuscript checks | 8 evidence-linked claims, 6 tables, 5 figure specifications, style audit PASS, 0 sentences over 40 words |
| Immutability | Byte-stable resume, fixture checksum mutation rejection, and artifact tamper rejection passed |

## Artifacts

- Schema: `agents/manuscripts/paper_a.v1.json`
- Fixture: `tests/fixtures/manuscripts/paper_a_fixture.json`
- Workflow: `src/biointerfaceos/paper_a_workflow.py`
- CLI and Make target: `src/biointerfaceos/cli.py`, `Makefile`
- Tests: `tests/manuscripts/test_paper_a_workflow.py`
- Manuscript package: `release/manuscripts/paper_a/`
- Receipt SHA-256: `f01d2380ab5f059e08bba91cb29649ea5a5c8d83e408e49286f45548ca2ecad1`
- Manifest SHA-256: `c6635c72dd5ad715bc4f77939a10e8204207915020afe69510bdca6a3787b8d8`
- Claim matrix SHA-256: `a4c55ab16daafe9d97f9030d0889e1c81447b057dc922ca64e3aaada05a1c947`
- Table manifest SHA-256: `80613611db7cecdbd5114d057bc37163b620779347939982786fad0fd5647446`
- Figure manifest SHA-256: `802829fb675f3cdec16e98106c84dc0e1f00136947ce93db12390531f709591f`
- Style audit SHA-256: `5f7190219c0b560235ee2284310d86fecd79a399476a5cf864a42addcc437ce2`

## Limitations

- The benchmark is a fixture-backed development release, not a production-scale evaluation.
- The protected target layer is excluded, so this task makes no hidden-test performance claim.
- Figure outputs are deterministic evidence-panel specifications; final journal graphics typesetting remains a submission-stage task.
- External related-work citations and journal-specific formatting are intentionally deferred until the manuscript package is reviewed against a target venue.

The next task is T106: draft Paper B method manuscript.
