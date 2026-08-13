# T143: Audit the executable external-evidence gate path

## Purpose

Make the second-round implementation path independently auditable after T133,
T135, T136 and T139. The audit checks that the contributor source package,
independent lockbox, external reproduction and editorial re-review stages are
ordered consistently across the handoff package, protocol, acceptance gates,
CLI and current blocked receipts.

This is a process-readiness result. It does not download a source, authenticate
an identity, accept a signature, admit a target, fit a model or create a
scientific result.

## Interface

```bash
python -m biointerfaceos project audit-r2-external-gate-path --strict
```

The receipt is written under
`reports/review_round_2/external_gate_path/v1.1.0/` and is read-only. Incoming
source bytes, protected observations, signatures and external identities stay
outside the repository until the appropriate preflight and scope audit pass.

## Required order

1. Source intake and licence gate.
2. Cross-laboratory target admission.
3. T121 amendment and real-model freeze.
4. Independent protected-data evaluation.
5. External scientific reproduction.
6. Editorial re-review and R2 acceptance.

The audit must also confirm that incomplete templates remain non-promotable,
the current T124 and T128 receipts remain blocked, and every external stage
has both pass evidence and a downgrade/fallback path.

## Acceptance evidence

- six ordered stages and six executable gate commands are present;
- the source and verification templates remain non-submittable;
- current handoff, T124 and R2 acceptance receipts retain all false scientific
  flags;
- all thirteen referenced process artifacts are hash-bound;
- the receipt is process-only and reports `scientific_submission_ready=false`.
