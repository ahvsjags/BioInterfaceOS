# Public handoff update — v0.1.3-r10.40

The current public handoff includes the exact r10.38 archive, DOI deposit
preparation metadata, and the T238 four-source fold-local target-membership
sensitivity receipt:

- Release: https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.40
- Scientific candidate: `v0.1.3-r10.32`
- DOI deposit metadata: `docs/release/R10_38_DOI_DEPOSIT_METADATA.json`
- r10.38 archive SHA-256: `69b1c7f83532e5d2b808ae704d8b11811fd9c72320b89989e273577e51ec26ef`
- T238 receipt: `reports/review_round_4/t238_four_source_availability_execution/v1.0.0/t238_four_source_availability_execution_receipt.json`
- Coordination issue: https://github.com/ahvsjags/BioInterfaceOS/issues/2

The metadata is ready for authenticated Zenodo or equivalent archive upload;
`doi_archived` remains false until the service returns an immutable locator and
the manifest/archive hashes are read back exactly. T238 remains
`DEVELOPMENT_OBSERVATION` and does not create an external receipt.
