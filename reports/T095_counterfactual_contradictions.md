# T095 Counterfactual ranking and contradiction evidence

## Result

T095 was completed on the KAUST Ibex server at implementation commit `25c9cae`.
The workflow froze two intervention families, checked positivity and OOD support before prediction, compared linear and protocol-adjusted models, abstained on unsupported or disagreeing cases, and preserved a contradiction graph with evidence links.

## Reproducible command

```bash
biointerfaceos discover counterfactuals --fixture
```

The command was run twice with deterministic resume behavior:

```text
COUNTERFACTUALS_VALID rows=5 interventions=2 supported=2 rejected=3 model_families=2 scored=2 abstentions=3 rank_pairs=1 rank_stability=1.000000 contradictions=3 unresolved=1 resumed=1
```

## Ranking and contradiction evidence

- Only two supported interventions were scored. Three cases were rejected/abstained: one positivity failure, one OOD-distance failure, and one model-disagreement failure.
- Two model families (`linear`, `protocol_adjusted`) produced one supported pairwise comparison with rank stability 1.0.
- Three contradiction edges were preserved: one resolved-by-protocol boundary, one model-disagreement edge, and one unresolved edge requiring independent assay replication.
- The language gate is `MODEL_BASED_HYPOTHESIS`; universal ranking and causal intervention wording are blocked.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T076, T090, T091, T093, and T094 checksums/contracts verified |
| Supported interventions | 2 scored; unsupported cases explicitly excluded |
| Positivity/OOD | Checked before prediction; 3 abstentions retained |
| Model comparison | 2 model families; rank stability 1.0 on supported pair |
| Contradictions | 3/3 edges preserved with evidence links; 1 unresolved |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 323 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Final repository gate | Dependencies, assets, catalog, lockbox, state, compileall, diff check, and immutable release verification passed |

## Artifacts

- Schema: `agents/discovery/counterfactuals.v1.json`
- Fixture: `tests/fixtures/omics/counterfactuals_fixture.json`
- Workflow and CLI: `src/biointerfaceos/counterfactual_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/omics/counterfactuals/`
- Focused tests: `tests/omics/test_counterfactual_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T096: implement the constrained multiobjective design baseline with mixture/structure constraints, uncertainty and AD penalties, observed-control recovery, and reproducible Pareto output.
