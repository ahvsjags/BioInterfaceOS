# T113 Run manuscript claim-to-evidence and language audit

## Result

T113 was completed on the KAUST Ibex server at implementation commit `7dea0e0`.
The audit covered the three frozen manuscript drafts, 24 claim-matrix entries,
246 sentences, and 47 evidence references. All sentence records received a
claim ID, every evidence reference resolved to a checksummed repository artifact,
and the language/citation/date gates reported zero critical findings.

## Reproducible command

```bash
make claim-audit
```

Observed first run:

```text
FINAL_CLAIM_AUDIT_VALID audit_id=bioif-final-claim-audit-v1.0.0 papers=3 claims=24 sentences=246 evidence=47 critical_findings=0 submission_blockers=0
```

A second invocation was rejected before overwrite:

```text
FINAL_CLAIM_AUDIT_INVALID: final claim audit already executed; overwrite refused
```

## Audit decisions

- Paper A and Paper B audited copies retain the frozen text and add an explicit
  audit addendum linking all scientific sentences to the claim/evidence ledger.
- Paper C retains the pre-lock draft verbatim and adds a post-lock metadata-only
  table with C1-C5 `POSTLOCK_REPLICATED`, `POSTLOCK_REFUTED`, and
  `POSTLOCK_INCONCLUSIVE` transitions. C6 remains association-only and C7 keeps
  OOD/selection limits.
- Positive causal, mechanistic, universal, broad-transfer, and experimental-
  validation wording is rejected unless explicitly guarded as a limitation.
- External citations are intentionally zero in these development drafts; the
  citation/date audit records this as `PASS_DEVELOPMENT_DRAFT_NO_EXTERNAL_CITATIONS`
  and verifies internal evidence references and the frozen date.

## Acceptance evidence

| Gate | Result |
|---|---|
| Focused claim-audit tests | 6 passed |
| Full test suite | 386 passed |
| Static checks | ruff, format check, mypy, compileall, and `git diff --check` passed |
| Repository checks | schema, assets, catalog, lockbox, release, and state passed |
| Sentence mapping | 246/246 mapped; orphan sentences 0 |
| Evidence mapping | 47/47 resolved; unresolved evidence 0 |
| Language gate | critical language findings 0; causal/mechanistic overclaims 0 |
| Manuscript outputs | 3 audited copies; submission blockers 0 |
| Boundary | protected values read false; raw values written false; public-package boundary consumed |
| Immutability | second audit rejected; receipt hash verification passed |

## Artifacts

- Schema: `agents/claim_audit/final.v1.json` (SHA-256 `a3b90ea31221071ba9f73d29e5cc0ac54abea5d828dd870d08ce5df7b1f023ca`)
- Fixture: `tests/fixtures/claim_audit/audit_fixture.json` (SHA-256 `fdfb86962b97c1a68c9a216802ec3ddc3f9bbcd07a15161fcff2b590c86ae898`)
- Workflow: `src/biointerfaceos/claim_audit_workflow.py` (SHA-256 `ba19b00963f34a0b2834e9e3a0201a08b6eb0bb36fd78da1a32c8065255c8f8c`)
- Tests: `tests/claim_audit/test_claim_audit_workflow.py` (SHA-256 `1dc23ac1e34166ed5c2a35754e2f5e1ef424f04b06924720e878c464258e76d5`)
- Final audit: `reports/claim_audit/final-v1.0.0/FINAL_CLAIM_AUDIT.json` (SHA-256 `bef40a9dc7230361d0027b75fcb34a8aed7f3e83dd652545a889ec9b044ee60c`)
- Audit receipt: `reports/claim_audit/final-v1.0.0/audit_receipt.json` (SHA-256 `d18474938b62735d7f914b96cb82ceb1e40522045ed7d685691f341696ad6f69`)
- Sentence map: `reports/claim_audit/final-v1.0.0/claim_sentence_map.json` (SHA-256 `29b343213dbb3e60d89f3c15610623996b70d752244ea164ac2777c3633ee618`)
- Evidence resolution: `reports/claim_audit/final-v1.0.0/evidence_resolution.json` (SHA-256 `9a303f74119510b534c81a5bbccad0e82b95ff0e41fb65886044650f755fb6f5`)
- Language audit: `reports/claim_audit/final-v1.0.0/language_audit.json` (SHA-256 `1e42c44e0dcf39d9668b50c1d634f0b89072de3896ca2132b9c0393566e22539`)
- Citation/date audit: `reports/claim_audit/final-v1.0.0/citation_date_audit.json` (SHA-256 `ce53cdc158e574b2661db53167b2866fbb57070dd107393c0a95aaf915865f91`)
- Audited manuscripts: `revised_manuscripts/paper_a_audited.md`, `paper_b_audited.md`, `paper_c_prelock_audited.md`
- Implementation commit: `7dea0e0`

## Limitations

- External related-work citations remain a submission-stage requirement for the
  development drafts and are not invented by this audit.
- The audit verifies wording and internal evidence scope; it does not add new
  experiments or protected raw values.
- Any future scientific claim must receive a new sentence-map/evidence receipt.

The next task is T114: run final project acceptance and produce the public release.
