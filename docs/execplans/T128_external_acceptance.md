# T128: External scientific reproduction, editorial re-review and R2 acceptance

## Purpose

Create the final R2 acceptance path: an external team reconstructs the scoped
empirical work and an independent editor maps every R2 finding to evidence or a
documented downgrade. Neither role may be performed by the author team.

## Preconditions

The protocol is ready, but T123 has no compatible real-model target, T124 has
no independent evaluator receipt, and T126--T127 are protocol-only. Thus no
external scientific reproduction or editorial acceptance can begin yet.

## Non-goals

Do not reclassify software replay as scientific reproduction, self-certify an
external team, create an editor signature, hide deviations, substitute a
fixture, or call the project submission-ready.

## Interfaces and invariants

- Protocol:
  `docs/data/R2_EXTERNAL_REPRODUCTION_AND_EDITORIAL_PROTOCOL.json`.
- Readiness command: `python -m biointerfaceos project accept-r2 --strict`.
- Outputs: `reports/review_round_2/r2_acceptance/v1.1.0/`.
- External receipt must disclose the team, affiliation, conflict status,
  checkout, environment, data provenance, commands, scope, deviations,
  results and signed attestation.
- Editorial report must disclose reviewer identity/conflicts and map every R2
  finding, with zero unexplained Critical findings for acceptance.

## Implementation plan

1. Freeze external-reproduction and editorial requirements before any result
   exists.
2. Read T123, T124, the two-route manuscript portfolio and current task
   statuses to issue a blocked readiness receipt when prerequisites are absent.
3. After real results and independent evaluation exist, issue a new protocol
   version naming the exact frozen artifacts to reproduce.
4. Receive external reproduction and editorial reports as external inputs;
   verify their scope, hashes, deviations and R2 finding matrix before release
   acceptance.

## Progress

- [x] 2026-08-12: Added a strict protocol and `project accept-r2` readiness
  command. It records six current blockers without pretending external work
  happened.
- [x] 2026-08-13: Updated the readiness audit to bind the latest portfolio,
  T123 result-profile receipt and both T129 CC0 non-admission receipts. These
  add explicit current target-admission blockers; they do not create a model,
  evaluator, reproduction or editorial result.
- [ ] T123 compatible target and frozen real-model results.
- [ ] T124 signed independent evaluator receipt.
- [ ] Completed T126/T127 manuscript evidence packages.
- [ ] External scientific reproduction and editorial re-review reports.

## Discoveries

The old T114 final-acceptance workflow is correctly superseded during R2. Its
fixture outputs cannot satisfy R2 external reproduction or editorial review.

## Decisions

The new command returns a valid blocked readiness audit rather than a false
acceptance. It separates internal preparation from external evidence and keeps
the project IN_PROGRESS until both external reports exist.

## Validation

- `python -m pytest tests/acceptance/test_r2_acceptance_workflow.py -q`
- `python -m biointerfaceos project accept-r2 --strict`
- `python scripts/validate_execution_pack.py`

The current receipt must show at least one blocker and all external receipt,
editorial review and submission-ready fields as `false`.

## Failure recovery

If an external report is incomplete, retain it as a documented failed attempt
and issue no submission designation. If a critical editorial finding remains,
return to the corresponding T123--T127 task and preserve the finding.

## Outputs

Protocol, readiness workflow and CLI, regression tests, immutable blocked
receipt, this ExecPlan, and later external reproduction/editorial inputs.

## Completion note

The acceptance path is prepared and audited. T128 remains blocked until
genuine external reproduction and independent editorial re-review are supplied.
