# T049 Consensus and Expert Review Packet Evidence

## Result

T049 is complete on the KAUST Ibex server. The review export is deterministic, stratified, blinded at source/record labels, and explicitly unsigned.

- sampling strategy: stratified
- packets: 3
- strata: 3
- strata covered: CONSENSUS_DISAGREEMENT, MISSING_EVIDENCE, BROKEN_LOCATOR
- unsigned packets: 3
- signed packets: 0
- expert-gold promoted: 0

Each packet carries an exact question, candidate values, evidence locators, annotation schema, and empty sign-off fields. No human sign-off was fabricated.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 192 tests passed; ruff, format, and mypy passed.
- biointerfaceos review export --sample stratified: exit 0; packets=3 strata=3 unsigned_packets=3 signed_packets=0.
- biointerfaceos data validate gold-auto --fixture: passed.
- biointerfaceos data validate silver --fixture: passed.
- biointerfaceos release verify bronze: passed.
- biointerfaceos evidence trace --fixture --locator asset:asset-table-001/table:table-main/cell:C3: passed; trace_matches=2.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos state validate: passed; tasks=115.
- compileall and git diff --check: passed.
- 23 append-only JSONL ledgers validate.

## Artifacts

- src/biointerfaceos/review_packets.py
- src/biointerfaceos/cli.py
- tests/fixtures/review/review_expectations.json
- tests/review_packets/test_review_packets.py
- reports/review_packets/packets.json (SHA-256: 8c361e93363e5e433c108a23f8c3b706b732c3dd08f9ff673c23d009cb7785fd)
- reports/review_packets/annotation_guide.json (SHA-256: 0f6bad40933b7ceed331cbfafa0380bf42c233634e4c06719cb88bfdc123b3ce)
- reports/review_packets/signoff_schema.json
- reports/review_packets/coverage_report.json (SHA-256: 2a7494a1314e2270f5183f1331d00d61527793363a54f83b65e1c0d56ee13e29)
- reports/review_packets/review_export_receipt.json (SHA-256: 1bcc363badc64bdab19bba0a9d401b9515759bd9ea66c745b5a979e23bbe39f2)
- docs/execplans/T049_consensus_review_packets.md
- sequence-45 record in reports/task_ledger.jsonl

## Limitations

- Packets are unsigned and do not constitute expert gold.
- Human review remains pending until a signed import is provided.
- No live endpoints, credentials, or locked-test payloads were accessed.
