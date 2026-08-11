# T048 Audited Gold-auto Subset Evidence

## Result

T048 is complete on the KAUST Ibex server. Gold-auto admission uses explicit confidence, dual-consensus, resolved-evidence, conflict, quarantine, and reverse-trace gates.

- release ID: bioif-gold-auto-3f7c4fba17b1a50e
- manifest hash: 3f7c4fba17b1a50eebb8d571deea6004670567fe4db5c18631d1470f67d36887
- minimum confidence: 0.85
- consensus agreement fields: 4
- disagreement fields: 1
- admitted fields: 3
- excluded fields retained in Silver: 2
- reverse traces: 3
- expert-gold admitted: 0

The outcome_mean disagreement and arm_label missing resolved evidence are explicit exclusions. Every admitted field has evidence assertion IDs and reverse-trace locators.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 190 tests passed; ruff, format, and mypy passed.
- biointerfaceos data build-gold-auto --fixture: exit 0; admitted_fields=3 excluded_fields=2 agreement_fields=4 disagreement_fields=1 reverse_traces=3.
- biointerfaceos data validate gold-auto --fixture: exit 0; exact rebuild, checksum, exclusion, and reverse-trace gates passed.
- biointerfaceos evidence trace --fixture --locator asset:asset-table-001/table:table-main/cell:C3: passed; trace_matches=2.
- biointerfaceos data validate silver --fixture: passed.
- biointerfaceos release verify bronze: passed.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos state validate: passed; tasks=115.
- compileall and git diff --check: passed.
- 23 append-only JSONL ledgers validate.

## Artifacts

- src/biointerfaceos/gold_auto.py
- src/biointerfaceos/cli.py
- tests/fixtures/gold_auto/gold_auto_expectations.json
- tests/gold_auto/test_gold_auto.py
- release/gold_auto/bioif-gold-auto-3f7c4fba17b1a50e/gold_auto_manifest.json (SHA-256: 0e2936cf0f202ee55bb799063275d1f3338de935e161f0f72ca6a0339ac33bf6)
- release/gold_auto/bioif-gold-auto-3f7c4fba17b1a50e/gold_auto_records.json
- release/gold_auto/bioif-gold-auto-3f7c4fba17b1a50e/gold_auto_exclusions.json (SHA-256: d5781613924b04cf107a15f01cd8b8429dadb2e8d72d763a2d995ae6b4d9572e)
- release/gold_auto/bioif-gold-auto-3f7c4fba17b1a50e/agreement_report.json (SHA-256: 155d9ffd5457fefd8d3bb4a57ac215da0bbf736bc394e5906b86b3bb259ddf62)
- release/gold_auto/bioif-gold-auto-3f7c4fba17b1a50e/reverse_trace.json
- release/gold_auto/bioif-gold-auto-3f7c4fba17b1a50e/rebuild_receipt.json (SHA-256: 260deed1cc10cac7a25f12be556b3c884dfc96e08a1714ee55de0f8ac2ba496b)
- docs/execplans/T048_gold_auto_subset.md
- sequence-44 record in reports/task_ledger.jsonl

## Limitations

- Selection is fixture-backed and does not replace expert review.
- Excluded rows remain in Silver with explicit reasons.
- No human expert sign-off was fabricated or inferred.
