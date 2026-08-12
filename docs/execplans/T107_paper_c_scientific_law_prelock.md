# T107 Draft Paper C scientific-law manuscript pre-lock

## Objective

Freeze a development manuscript for the strongest scientific-law candidates
before any lockbox evaluation. Use T090, T091, T092, T093, T094, T095, T100,
and T101 as the evidence boundary.

The package must define candidate laws, exact analyses, plots, predictions, and
allowed wording. It must distinguish development discoveries from prospective
lockbox outcomes. It must not view, infer, or summarize lockbox payloads.

## Claim boundary

- Use only checksum-pinned development reports and their preregistered outputs.
- Narrow candidates to laws with replicated or convergent development evidence.
- Preserve the T100 OOD narrowing and the T101 selection-sensitivity downgrade.
- Keep mediation, cross-species, symbolic, protocol, and counterfactual claims
  within the wording approved by their upstream reports.
- Record predicted lockbox outcomes without accessing the lockbox.

## Implementation steps

1. Add a versioned Paper C pre-lock schema and checksum fixture.
2. Implement a deterministic `paper-c-prelock` workflow with candidate-law
   cards, prediction table, exact analysis/plot definitions, claim matrix,
   manuscript draft, manifest, and receipt.
3. Add focused tests for generation, resume, input checksum mutation, and
   artifact tampering.
4. Add the CLI command and `make paper-c-prelock` target.
5. Run the complete offline gate and repository validation commands.
6. Record T107 and activate T108 only after all acceptance checks pass.

## Acceptance criteria

- Every law candidate links to development evidence and reports its strength.
- Exact analyses and plots are frozen before lockbox access.
- The package contains allowed wording, predicted outcomes, and explicit
  abstention criteria.
- No lockbox payload, protected result, or post-lockbox interpretation appears.
- Resume and mutation/tamper rejection pass without overwriting artifacts.

## Fallback

If a candidate lacks convergent evidence, retain it as a bounded exploratory
candidate or remove it from the primary manuscript. Do not use exploratory
patterns to create broad causal or universal claims.
