# BioInterfaceOS external evidence request — r10.56

This page is an execution request for independent laboratories, methods groups and software users. It is not an external receipt. The repository currently has no verified non-author lockbox result, no-author reproduction result, external adoption record or DOI archive read-back; all corresponding gate fields remain `false`.

## Fixed candidate

Use the immutable GitHub tag `v0.1.3-r10.56` and verify that it resolves to:

```text
2b5642f480576e70e362a11fcfe4757420e93f80
```

The release manifest is `release/empirical_candidate_v0.1.3-r10.56/release_manifest.json` with SHA-256:

```text
553febabf2d6595dd52545c6b75035e901c20c8ef07b1cb69df4e332aeb4a56d
```

The paper-data route is intentionally narrow and auditable: four laboratory anchors, seven canonical targets, 783 raw observations, 671 observations after pre-model technical-replicate collapsing, 112 collapsed biological/sample groups and 115 measurement batches. It is a paper-derived portability benchmark, not a claim of four independent biological cohorts.

## Available roles

1. **Protected lockbox evaluator.** The evaluator obtains and controls a row-level input that is never disclosed to the authors and returns aggregate endpoint, effective-count, paired-ablation, negative-control, OOD and uncertainty results.
2. **No-author reproduction team.** The team reacquires the public paper/supplement files independently, performs a clean clone and runs the prescribed T250 route without author assistance during execution.
3. **External users.** Two distinct non-author users or institutions install the fixed tag in fresh environments and perform distinct real tasks. Fixture-only runs, page views, downloads, stars and author-controlled accounts do not count.

## Required evidence

Every submitted receipt must bind the fixed tag and commit, protocol and dependency hashes, input provenance or protected-data attestation, environment fingerprint, exact commands, stdout/stderr and output hashes, failures and deviations, complete result summary, conflict-of-interest statement, signed attestation and an immutable archive locator. Preserve negative and failed runs; do not submit only successful results.

For the protected role, the evaluator must state that row-level inputs were evaluator-controlled, authors had no row-level access and only aggregate results were returned. For the reproduction role, the team must state that source files were reacquired or independently attested and that no author assistance was used during the run. For adoption, record the real task, input scope, install environment and limitations.

## Execution and structural preflight

The clean-room route is:

```bash
bash scripts/r4_external_reproduction_r10_54.sh /path/to/fresh-output
```

After the four signed JSON receipts have been produced, place them under a private `external_receipts/` directory, fill the bundle from `docs/data/R4_T279_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`, set each document SHA-256, and run:

```bash
uv run biointerfaceos data preflight-r4-t279-external-receipts \
  --bundle external_receipt_bundle.json \
  --documents-root external_receipts \
  --receipt-out r4_t279_preflight_receipt.json \
  --strict
```

Structural preflight checks byte identity, schema, fixed-release binding and declared safeguards. It deliberately does not authenticate a person's identity, prove independence or convert a submission into scientific evidence. Those checks require editorial review of the real participant and archive records.

## Submission route and claim boundary

Return the completed bundle and archive locators to the project maintainers through the project’s agreed private exchange. Do not upload protected row-level input or intermediate protected outputs to a public issue. A public issue comment can announce that a handoff occurred, but it is not itself an evaluator receipt.

Until the receipts are independently checked and an archival DOI provides an exact manifest/archive read-back, the only permitted claim level is exploratory paper-derived execution. `scientific_submission_ready` must remain `false`.
