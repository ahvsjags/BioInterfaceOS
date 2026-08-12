# T098 Candidate audit packets and retrospective validation

## Result

T098 was completed on the KAUST Ibex server at implementation commit `759b496`.
The workflow deduplicates design fingerprints, builds provenance-complete cards,
checks AD/uncertainty/nearest-evidence and perturbation stability, excludes unsafe
or unsupported candidates, and evaluates later evidence metadata descriptively
without tuning selection.

## Reproducible command

```bash
biointerfaceos design audit-candidates --fixture
```

The command was run twice with deterministic resume behavior:

```text
DESIGN_AUDIT_VALID candidates=7 unique_candidates=6 duplicate_candidates=1 supported_candidates=3 rejected_candidates=4 temporal_matches=2 unresolved_matches=1 abstentions=3 selected_wording=exploratory_supported resumed=1
```

## Candidate and retrospective evidence

- Seven raw candidates reduced to six unique fingerprints; one duplicate was
  excluded without changing the candidate selection policy.
- Three low-OOD, low-uncertainty, nearest-evidence-supported candidates produced
  cards with component/geometry/conditioning provenance and the allowed wording
  `exploratory_supported`.
- Four candidates were rejected or abstained: high AD/uncertainty, perturbation
  instability, and unsafe structure. Each reason remains in the abstention ledger.
- Two temporal matches and one unresolved/non-temporal match were retained as
  descriptive metadata only. Every retrospective row records
  `used_for_selection=false`.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T096 and T097 receipts verified by checksum and status |
| Deduplication | 7 raw candidates, 6 unique, 1 duplicate ledger entry |
| Candidate cards | 3 supported cards with provenance, AD, uncertainty, nearest evidence, stability, and wording |
| Exclusion policy | 4 rejected candidates retained; high-OOD/unstable/unsafe outputs excluded |
| Retrospective matching | 2 temporal, 1 unresolved; descriptive only and never used for selection |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 329 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Final repository gate | Lockfile, schema, assets, catalog, lockbox, immutable release, state, compileall, and diff checks passed |

## Artifacts

- Schema: `agents/design/candidate_audit.v1.json`
- Fixture: `tests/fixtures/design/candidate_audit_fixture.json`
- Workflow and CLI: `src/biointerfaceos/candidate_audit_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/design/candidates/`
- Focused tests: `tests/design/test_candidate_audit_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T099: run the mandatory model and data ablation matrix.
