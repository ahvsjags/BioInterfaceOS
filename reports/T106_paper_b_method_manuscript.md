# T106 Draft Paper B method manuscript

## Result

T106 was completed on the KAUST Ibex server at implementation commit `2ec2db9`.
The workflow creates an evidence-linked method manuscript from the frozen
`bioif-data-model-dev-v1.0.0` release, T088 agent evidence, T099 paired
ablations, and T100 OOD sensitivity evidence.

## Reproducible command

```bash
make paper-b
```

Observed first and resumed runs:

```text
PAPER_B_VALID release_id=bioif-data-model-dev-v1.0.0 data_layers=2 model_layers=2 ablations=5 ood_rows=12 claims=8 tables=6 figures=5 evidence_inputs=15 style_passed=true resumed=0 target_values_exposed=false
PAPER_B_VALID release_id=bioif-data-model-dev-v1.0.0 data_layers=2 model_layers=2 ablations=5 ood_rows=12 claims=8 tables=6 figures=5 evidence_inputs=15 style_passed=true resumed=1 target_values_exposed=false
```

## Method evidence boundary

The fixture pins 15 inputs. They include the T104 release manifest, freeze
manifest, freeze receipt, and data/model card. It also includes the T088 agent
report, five T099 ablation artifacts, and five T100 OOD artifacts. No protected
test value, lockbox payload, external download, credential, or network resource
was accessed.

## Main method results

| Component | Result |
|---|---|
| Frozen release | 8 Silver tables, 3 Gold-auto rows, 2 model layers, 6 thresholds, 4 dependency entries |
| Selected policies | `conservative_conformal` uncertainty and `material_protocol_masked` multimodal representation |
| Paired ablations | Five essential modules, four paired units per module, budget 8, same splits |
| Ablation effect | Mean full-minus-ablated effect 0.081; largest fixture effect 0.110 for candidate-audit support |
| OOD sensitivity | Six outcome-independent dimensions, 12 groups, 6 low-n groups, 3 sensitivity scenarios |
| Applicability gate | `NARROWED_BY_OOD`; low-n groups remain abstained |
| Agent method check | Seven tasks, three modes, single-agent selected, all six fixture quality metrics 1.000 |

## Acceptance evidence

| Gate | Result |
|---|---|
| Full test suite | 349 passed |
| Lock and environment | `uv lock --check` and frozen `uv sync` passed |
| Static checks | ruff check, ruff format check, mypy, compileall, and `git diff --check` passed |
| Repository checks | Schema, assets, catalog, lockbox, immutable release, and project state passed |
| Manuscript checks | 8 evidence-linked claims, 6 tables, 5 figure specifications, style audit PASS, 0 sentences over 40 words |
| Immutability | Byte-stable resume, fixture checksum mutation rejection, and artifact tamper rejection passed |

## Artifacts

- Schema: `agents/manuscripts/paper_b.v1.json` (SHA-256 `6abf15255a9f6f46af58abb78dc9eef914ba07fc0f73fb6611a38afbf077742b`)
- Fixture: `tests/fixtures/manuscripts/paper_b_fixture.json` (SHA-256 `92682dfae9beee526b6a17337be7bd3291750806c71a47524b9c19a9e961a7cf`)
- Workflow: `src/biointerfaceos/paper_b_workflow.py` (SHA-256 `311bcf06e045fea72f8ce34cfdde97aead5a3107f8d4651850934ad9d5cbb585`)
- Tests: `tests/manuscripts/test_paper_b_workflow.py` (SHA-256 `bff2910dc881f6981f8ce7daa1b8ccb801d16b4472cddda10cb99249e74be09e`)
- Manuscript package: `release/manuscripts/paper_b/`
- Receipt SHA-256: `2c1bdec970c3ed31a103d8fb47e6aa3da077a09f5301b50b1e8e8b822e3ee9df`
- Manifest SHA-256: `4d378e88ba685f7b8584d0248ff8207269cdb286af38ab95624ceefddc22a522`
- Claim matrix SHA-256: `2c331bbb33442692a0225c03d4e4412fc8d2d3d6e56284f49eae28a1779a83ca`
- Table manifest SHA-256: `cf17eb65d0d5dbfb21f10dbd15e846e7941c1eeae34e7c25a7e1fe23e95dde8b`
- Figure manifest SHA-256: `20e123395d4e5cc78a1801a1241ae938f52e9abfe00e0b55dcbd26923456b3bd`
- Style audit SHA-256: `5146259a63555ea1c4fb25af63f2ebc601c519300790948f483db5cb9240d4c0`

## Limitations

- The release is fixture-backed and development-scoped.
- Data and model artifacts remain analysis-only.
- The paired ablation result does not establish a causal decomposition.
- Six low-n groups narrow applicability and remain abstained.
- One non-essential provider-backed raw-data ablation remains interface-blocked.
- Agent evidence tests fixture execution, not live-source behavior.
- External citations and venue formatting remain submission-stage work.

The next task is T107: draft Paper C scientific-law manuscript pre-lock.
