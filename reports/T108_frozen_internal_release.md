# T108 Create signed internal frozen release before lockbox

## Result

T108 was completed on the KAUST Ibex server. The strict internal release was
created from clean tree at implementation commit `d5ec0cb`.

The release binds 25 development inputs, 24 claim slots, 3 manuscripts, 15
figure specifications, and the Paper C pre-lock prediction package. Its
authorization scope is evaluator-only. Development code did not access the
lockbox.

## Reproducible commands

```bash
make freeze-prelock
biointerfaceos release verify-prelock
```

Observed first and resumed strict freezes:

```text
PRELOCK_RELEASE_VALID release_id=bioif-internal-prelock-v1.0.0 commit=d5ec0cbccf7a inputs=25 claims=24 manuscripts=3 figures=15 signature=1b01957a0009dd770fa7d83a0d30bc939e03ad049dfac62602e7f2132513f52f authorization_scope=evaluator_only lockbox_accessed=false resumed=0
PRELOCK_RELEASE_VALID release_id=bioif-internal-prelock-v1.0.0 commit=d5ec0cbccf7a inputs=25 claims=24 manuscripts=3 figures=15 signature=1b01957a0009dd770fa7d83a0d30bc939e03ad049dfac62602e7f2132513f authorization_scope=evaluator_only lockbox_accessed=false resumed=1
PRELOCK_RELEASE_VERIFIED release_id=bioif-internal-prelock-v1.0.0 inputs=25 signature=1b01957a0009dd770fa7d83a0d30bc939e03ad049dfac62602e7f2132513f authorization_scope=evaluator_only lockbox_accessed=false
```

## Freeze boundary

The release includes T103 benchmark artifacts, T104 data/model configuration
and release metadata, T105 Paper A, T106 Paper B, and T107 Paper C pre-lock
artifacts. The manifest records target values excluded, lockbox access false,
and a domain-separated SHA-256 signature.

The authorization file is marked `not_for_development=true`. The lockbox plan
permits only evaluator execution of predeclared predictions and a sealed
evaluator receipt. It blocks release modification, prediction rewriting, and
development access.

## Acceptance evidence

| Gate | Result |
|---|---|
| Full test suite | 358 passed |
| Lock and environment | `uv lock --check` and frozen `uv sync` passed |
| Static checks | ruff check, ruff format check, mypy, compileall, and `git diff --check` passed |
| Repository checks | Schema, assets, catalog, lockbox, data release, and project state passed |
| Strict freeze | Clean tree required and passed; 25 inputs hash-verified |
| Immutability | First freeze, byte-stable resume, signature verification, checksum mutation, artifact tampering, dirty-tree rejection, and authorization-boundary tests passed |
| Protected boundary | `lockbox_accessed=false`, `target_values_exposed=false` |

## Artifacts

- Schema: `agents/release/prelock.v1.json` (SHA-256 `89a3030e0bd75121f8c4ef4a84f7da7d5bb144644cbc0133c56b095f2aebcab4`)
- Fixture: `tests/fixtures/release/prelock_fixture.json` (SHA-256 `8cd49fa773d0fc07a85b7eac5ed9456cc1f7a01c169625b400de4087071c2a64`)
- Workflow: `src/biointerfaceos/prelock_release_workflow.py` (SHA-256 `344e929044e01fa8c73d534ccab13d16f30e30ceac48d6ebba25a451836ee738`)
- Tests: `tests/release/test_prelock_release.py` (SHA-256 `9dd88f88f4a4cd27093bf53342e3e83644d270af87ca1403e94eed4b4908147d`)
- Release directory: `release/internal_prelock/bioif-internal-prelock-v1.0.0/`
- Release manifest SHA-256: `9fe93b2902e332ed5efbf7743408e3875e4390e060fec931fd2a962132f3f7d2`
- Release receipt SHA-256: `904e2085750cf4765eab7a796a2c88a2cf56cada491de04ac6f284701f83c90b`
- Signature SHA-256: `a7003c9d1f73ae960310c7816e65d2e43d3ba5385ed5b24653b1087624bfa0bb`
- Lockbox plan SHA-256: `4ec8243234c43db77c4990cec3ab6aa52ba2f73b7e6afae0abefdceafe6f998e`
- Evaluator authorization SHA-256: `279806d10be65eefe8bf73ffaea9f9fe0a3fe131d9144d005deccd0454f6fb88`
- Input checksums SHA-256: `19fd579590f7ef654f9fbef00d7efe6c7fa3c605c2aade2242aa3df4c147ed3a`
- Signature: `1b01957a0009dd770fa7d83a0d30bc939e03ad049dfac62602e7f2132513f52f`

## Limitations

- The release is an internal development freeze, not a public data release.
- Protected test values remain unread and are not part of the release.
- Evaluator authorization is metadata for the next task and is not used by development workflows.
- Any changed input or claim requires a new freeze candidate.

The next task is T109: execute the one-shot locked 2025–2026 evaluation.
