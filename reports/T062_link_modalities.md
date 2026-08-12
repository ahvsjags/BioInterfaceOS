# T062 corona-to-response modality-link evidence

## Result

The server now runs `biointerfaceos omics link-modalities --fixture` using hash-verified T056 corona modules, T061 signature scores/registry, and T047 Silver evidence. Three link candidates are explicitly stratified: one declared direct matched-unit candidate, one indirect literature-level candidate, and one unmatched candidate retained only in the exclusion ledger.

The output contains two candidate mechanism cards, no pseudo-pairs, no cross-study expression merge, and no causal claims. Direct evidence includes an explicit `MU-001` matched-unit key; indirect evidence has an evidence locator but no response sample IDs; the unmatched candidate is excluded with `no_shared_study_or_declared_matched_unit`.

## Validation

```text
LINK_MODALITIES_VALID links_attempted=3 direct=1 indirect=1 unmatched=1 candidate_cards=2 resumed=0 pseudo_pairs=false causal_claims=false
LINK_MODALITIES_VALID links_attempted=3 direct=1 indirect=1 unmatched=1 candidate_cards=2 resumed=1 pseudo_pairs=false causal_claims=false
3 focused modality-link tests passed
229 full tests passed
```

The final offline gate also passed UV lock/sync, Ruff, formatting, mypy, assets, catalog, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- T056 module/mapping, T061 score/registry, and T047 evidence hashes were checked before link construction.
- Direct links require module and response sample IDs, a declared matched-unit key, match basis, and evidence locator.
- Indirect links preserve module samples but have no response sample IDs or matched-unit key; they remain low-confidence candidate mechanisms.
- Unmatched candidates are not promoted and remain in the append-only exclusion ledger.
- No pseudo-pairing, causal wording, live network, raw download, credential, or locked payload access occurred.

## Artifacts

- Implementation commit: `401971c`.
- Fixture: `tests/fixtures/omics/link_modalities_fixture.json`, SHA-256 `afce37be882d9bdf4804c787b3495e3ff029dbc67c514973ac580fbdcf43fe5f`.
- Link graph: `reports/omics/modality_links/link_graph.json`, SHA-256 `8833ff32e4ce55f2d502696119bc64431ecfb987a396fa888d8de20a2e9e6dbe`.
- Direct stratum: `reports/omics/modality_links/direct_strata.json`, SHA-256 `facf4ad230083a84d4a7571cfd0b4076ab9e41de735e0c1ddd5b06e1cd21b8a`.
- Indirect stratum: `reports/omics/modality_links/indirect_strata.json`, SHA-256 `48f3aa3b6d60ef641f6935c34ec3e54baba063cc5c0c638db4c01063bc917435`.
- Candidate cards: `reports/omics/modality_links/candidate_mechanism_cards.json`, SHA-256 `90ffacfa9e227cf8e97c1461a0b62555ff4daf794f95fffe87d5e3402290b9f6`.
- Pairing audit: `reports/omics/modality_links/pairing_audit.json`, SHA-256 `98a087353afb5b15a5a1ccc4a4cfe3268eafac7af7a7428f432ca74c9c8e2644`.
- Exclusion ledger: `reports/omics/modality_links/exclusion_ledger.json`, SHA-256 `9b1257f36bca9cc95f43dcbd272d02eed1c854cb3019c17f2a3ecc67e1677b48`.
- Processing receipt: `reports/omics/modality_links/processing_receipt.json`, SHA-256 `cdb9e1617904ef871a757a813d9880a15c6797d01ce1c3358d0787ac1e2ab5dd`.

The first run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes.
