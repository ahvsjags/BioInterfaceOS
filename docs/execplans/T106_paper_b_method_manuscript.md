# T106 Draft Paper B method manuscript

## Objective

Draft a method-focused Paper B manuscript from the validated development data/model
release in T104, the extraction and coverage evidence in T088, the ablation
evidence in T099, and the leave-group/OOD sensitivity evidence in T100.

The manuscript must explain the method boundary, data and model layers,
uncertainty policy, missingness handling, ablation design, OOD abstention, and
agent evaluation. It must distinguish implementation evidence from scientific
claims and exclude unsupported causal, prospective, or production-performance
language.

## Inputs and claim boundary

- Use only checksum-pinned artifacts from T104, T088, T099, and T100.
- Preserve the development-release status and analysis-only licensing boundary.
- Report the selected conservative uncertainty policy and the selected
  material/protocol-masked multimodal representation only where the frozen
  receipts support them.
- Keep OOD and low-n groups abstained where the upstream report requires it.
- Do not include locked targets, hidden test values, causal intervention claims,
  or unsupported claims for failed/non-essential modules.

## Implementation steps

1. Add a versioned Paper B manuscript schema and checksum fixture.
2. Implement a deterministic `paper-b` workflow that verifies all upstream
   receipts before rendering the manuscript, claim matrix, tables, figures,
   style audit, manifest, and receipt.
3. Add focused tests for generation, byte-stable resume, input checksum
   mutation, and artifact tampering.
4. Add the CLI command and `make paper-b` target.
5. Run the full offline gate and all repository validation commands.
6. Record the evidence report, update the task state, and activate T107 only
   after the T106 acceptance gate passes.

## Acceptance criteria

- Every numeric method claim links to a checksum-pinned upstream artifact.
- The manuscript includes explicit failure modes, OOD abstentions, missingness,
  and limitations.
- No hidden target value, causal claim, or production-scale claim is emitted.
- First generation, resume, checksum mutation rejection, and tamper rejection
  pass.
- Full project gates pass with no network or raw-data access.

## Fallback

If a requested novelty or causal claim is not supported by T104/T088/T099/T100,
remove the claim and retain the strongest validated method description. Failed
or non-essential modules remain limitations rather than being promoted to
positive results.
