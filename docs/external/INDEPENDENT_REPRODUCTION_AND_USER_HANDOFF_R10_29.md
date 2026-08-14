# Independent external evidence handoff for v0.1.3-r10.29

This document is an open execution request, not a completed external receipt.
The release is the immutable tag `v0.1.3-r10.29` at commit
`2cecba46a5b51af6f8a00aaeec8a5294dc96313b`, with overlay manifest
`release/empirical_candidate_v0.1.3-r10.29/release_manifest.json` whose SHA-256
is `4d49bc2ff6be959cd0c09495682b2571e6263f3747d3f879847f4375f11a706a`.

## Fixed checkout

```bash
git clone --branch v0.1.3-r10.29 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
test "$(git rev-parse 'v0.1.3-r10.29^{}')" = "2cecba46a5b51af6f8a00aaeec8a5294dc96313b"
test "$(sha256sum release/empirical_candidate_v0.1.3-r10.29/release_manifest.json | awk '{print $1}')" = "4d49bc2ff6be959cd0c09495682b2571e6263f3747d3f879847f4375f11a706a"
uv sync --locked --all-groups
```

## Three independent work packages

1. **Non-author lockbox evaluator.** Hold a protected held-out input or unseen
   real dataset outside the author project. Return aggregate primary estimand,
   cluster-aware uncertainty, effective counts, paired composition ablation,
   within-batch permutation negative control, failures and deviations. Do not
   share row-level values or intermediate outputs with the authors.
2. **No-author scientific reproduction.** Independently reacquire the public
   CC-BY-3.0 PMC6592156 supplementary route and run:
   `bash scripts/r4_external_reproduction.sh reports/external_reproduction/<id>`.
   Preserve source/download hashes, environment digest, commands, stdout/stderr,
   output hashes, failed runs and signed identity/COI statement.
3. **External adoption.** Two distinct non-author users or institutions install
   the fixed tag in clean environments and perform materially different real
   tasks. Each submits task provenance, environment/dependency hashes, outputs,
   failures, limitations and an immutable receipt locator.

Every receipt must state identity, institution, role, conflict disclosure,
fixed tag/commit, protocol hash, input or protected-data attestation, commands,
environment digest, output hashes, deviations, failures and signed attestation.
The existing preflight template is only structural; it cannot authenticate an
identity or promote `scientific_submission_ready`.

The current paper-data evidence is deliberately bounded: PMC11328176 is a
technical six-core sensitivity route on one common prepared material, not six
independent biological cohorts. The current gate therefore remains false until
real non-author receipts and a DOI/archive read-back are independently audited.
