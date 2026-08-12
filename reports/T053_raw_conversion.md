# T053 raw mass-spec conversion evidence

## Result

The bounded fixture workflow completed one public, supported mzML bypass for `PXD000001` and refused four inputs with explicit reasons: restricted access, declared oversize, unsupported vendor RAW, and checksum mismatch. The workflow never downloaded a raw payload or accessed locked content.

The completed record retained `Orbitrap Fusion` instrument metadata. The 171-byte fixture was copied through the `mzml_bypass` converter (`fixture-bypass-v1`); input and output SHA-256 were both `556f2768a34cdbc53e8db91feff6877634b60719f006d67e892d12cba5e7424f`. A repeated run reused the same artifact and returned `resumed=1` with byte-identical receipt content.

## Validation

```text
CONVERSION_VALID records=5 completed=1 refused=4 resumed=1 raw_downloaded=false locked_payload_accessed=false
5 focused conversion/omics tests passed
202 full tests passed
```

The offline gate also passed UV lock/sync, Ruff, formatting, mypy, PRIDE triage, data coverage, Silver and Gold-auto validation, review export, asset verification, catalog check, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Artifacts

- Fixture: `tests/fixtures/omics/conversion_fixture.json`, SHA-256 `0e0c44e085213b90bbb53f0063fcc75a9576ebb816ce8c45bb5a9f5986957ca9`.
- Manifest: `reports/omics/conversion/conversion_manifest.json`, SHA-256 `18929567250fe5edee2b5bbf076bec257399736f58a2dd1a2d5d9b4a0a03d1dc`.
- Log: `reports/omics/conversion/conversion_log.json`, SHA-256 `78552fcea8ffc9e8b629a9880b7660ea5f49b6b71cfb1c429bc2123e00670802`.
- Receipt: `reports/omics/conversion/conversion_receipt.json`, SHA-256 `2c58c5921b2bfc09d36448ce94e851598ab0e350d6807c8e8b4b2309c9fb211f`.
- mzML artifact: `reports/omics/conversion/artifacts/PXD000001.mzML`, SHA-256 `556f2768a34cdbc53e8db91feff6877634b60719f006d67e892d12cba5e7424f`.

The vendor RAW path remains intentionally unavailable in this bounded workflow; the refusal is recorded instead of being presented as a successful conversion.
