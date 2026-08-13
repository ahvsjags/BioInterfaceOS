# T137: Refresh the current R2 public-release and software-replay receipts

## Purpose

T135 and T136 added public, executable preflight modules and non-submittable
templates after the previous public-release audit and software-replay receipts.
Create new immutable receipts from the current tracked source tree rather than
describing the earlier receipts as current.

## Scope and invariants

- Keep historical `v1.2.7` public-audit and `v1.3.0` replay outputs immutable.
- Rebuild a default-deny public inventory at `v1.2.9` and a clean public-source
  software replay at `v1.5.0` from the final T137-complete source tree.
- Require the source manifest to contain both T135/T136 modules and both
  contributor-facing templates.
- Refresh the external-handoff and remediation receipts so their hash-bound
  source inventories point at the current public audit and expose the two
  preflight templates.
- Do not admit a target, receive a source, authenticate an external identity,
  fit a model, or alter any scientific-submission-ready flag.

## Validation

```bash
python -m biointerfaceos release audit-public --strict
python -m biointerfaceos reproduce release --strict
python -m biointerfaceos project audit-r2-external-handoff --strict
python -m biointerfaceos project audit-r2-remediation --strict
python -m pytest tests/release/test_public_release_audit_workflow.py tests/release/test_r2_release_reproduction_workflow.py tests/review_round_2/test_r2_external_handoff_workflow.py tests/review_round_2/test_r2_remediation_workflow.py -q
python -m biointerfaceos state validate
```

## Completion evidence

- `reports/review_round_2/public_release_audit/v1.2.9/`.
- `reports/review_round_2/reproducibility/r2_software_replay/v1.5.0/`.
- `reports/review_round_2/external_evidence_handoff/v1.4.0/`.
- `reports/review_round_2/remediation_status/v1.11.0/`.

The refresh demonstrates reproducibility of the current public software scope
only.  The T129, T124 and T128 empirical and independent-evidence gates remain
open.
