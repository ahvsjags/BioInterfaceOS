# R4-T293 self-service external reproduction

This page is an executable invitation for a genuinely non-author team. It is not a receipt and does not close any evidence gate. The reproducing team must work without author assistance during execution, preserve failures and negative results, and submit a signed aggregate receipt at an immutable public locator.

## Fixed scientific checkout

Run the scientific work from the immutable tag, not from the moving coordination branch:

```bash
git clone --branch v0.1.3-r10.57 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git biointerfaceos-r10.57
cd biointerfaceos-r10.57
test "$(git rev-parse HEAD)" = "3557fac2019e57fd8968cdcf55b106750eafa750"
test "$(git describe --tags --exact-match)" = "v0.1.3-r10.57"
test -z "$(git status --porcelain)"
```

Before execution, independently reacquire every public input through the accession/URL recorded by the source registry. Do not copy a local author worktree, author-generated report directory or intermediate prediction file into the run.

## Fresh run

Choose a new output directory outside the checkout and run:

```bash
bash scripts/r4_external_reproduction_r10_57.sh /absolute/path/to/fresh-run-directory
```

The helper clones the fixed tag again, installs the locked environment, runs the frozen T250 four-laboratory common-target route, records environment/input/output hashes and preserves stdout/stderr. The helper's output is an execution bundle, not an accepted receipt.

For an independent real-task adoption report, run one materially distinct task from the fixed tag, record the task-specific input accession/scope, and preserve the complete command log. A fixture-only test, a page view, a download, a star or an author-run replay does not count.

## Receipt submission requirements

The team must submit, without protected row-level data:

- institution/team, role and conflict-of-interest disclosure;
- fixed tag, dereferenced commit, protocol and dependency hashes;
- independent input provenance or protected-input custody attestation;
- OS, Python/uv/container fingerprint, exact commands and complete stdout/stderr;
- output hashes and all failures, deviations, negative runs and limitations;
- signed attestation and immutable archive locator.

For a protected lockbox, the evaluator must retain row-level input and intermediate outputs, return aggregate-only results and prevent author access until the signed receipt is finalized. Internal agents, author-controlled KAUST replay, synthetic fixtures and success-only summaries are prohibited substitutes.

Submit the public non-sensitive summary through GitHub Issue #2 or the independent-reproduction issue form. Do not put credentials, private human data, protected inputs or hidden evaluator payloads in GitHub.

The project must keep `verified_no_author_reproduction_count`, `verified_distinct_adoption_receipt_count`, `verified_lockbox_receipt_count`, `doi_archive_verified` and `scientific_submission_ready` false until the actual external identity, custody and immutable archive records are independently audited.

