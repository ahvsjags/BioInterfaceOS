# Current external reproduction handoff — scientific candidate r10.32

The scientific code/data candidate is the immutable tag `v0.1.3-r10.32`.
The current public handoff overlay `v0.1.3-r10.35` contains the helper script
and current instructions; it does not add scientific results.

## Clean checkout and independent reacquisition

```bash
git clone --branch v0.1.3-r10.32 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git biointerfaceos-r10.32
cd biointerfaceos-r10.32
test "$(git rev-parse 'v0.1.3-r10.32^{}')" = "b8331e647d4194b85f68feb6e2d9e30a4f9e0a9d"
test "$(sha256sum release/empirical_candidate_v0.1.3-r10.32/release_manifest.json | awk '{print $1}')" = "d56a070a974675be2e3cff217c437d451eb765719ee95cc9c836abebf40c0c51"
test -z "$(git status --porcelain)"
```

Independently reacquire the public PMC6592156 supplementary/accession bytes,
record the download URL, local SHA-256 and any failed/negative download or
parsing attempt. Do not tune the run to the expected counts in the protocol.

Download the helper from the public r10.35 overlay into a directory outside
`biointerfaceos-r10.32`, record its SHA-256, and invoke it while the current
working directory is the clean r10.32 checkout:

```bash
curl -L --fail --output /tmp/r4_external_reproduction_r10_32.sh \
  https://raw.githubusercontent.com/ahvsjags/BioInterfaceOS/v0.1.3-r10.35/scripts/r4_external_reproduction_r10_32.sh
sha256sum /tmp/r4_external_reproduction_r10_32.sh
bash /tmp/r4_external_reproduction_r10_32.sh reports/external_reproduction/<independent_id>
```

The helper rejects moving branches, dirty scientific checkouts and manifest
drift; creates fresh output roots; reruns the public source audit and external
OOD route; records environment/dependency/output hashes; and never promotes a
claim. Submit the resulting hashes, commands, deviations, failures/negative
runs, identity/COI declaration, signed attestation and immutable archive
locator through the T218 receipt bundle.

This handoff is an executable route, not a reproduction receipt. Only a real
non-author team’s independently archived receipt can close the external
scientific-reproduction gate.
