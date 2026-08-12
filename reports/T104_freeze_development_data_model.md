# T104 Freeze development data and model release

## Result

T104 was completed on the KAUST Ibex server at implementation commit `358259b`.
The new `release freeze-dev` workflow verifies checksum-pinned Silver/Gold data,
PRIDE QC, modality links, uncertainty and multimodal model receipts, configs,
model results, and the T102 strict robustness gate before emitting an immutable
data/model release.

## Reproducible command

```bash
biointerfaceos release freeze-dev --fixture
```

Observed first and resumed runs:

```text
DEVELOPMENT_RELEASE_VALID release_id=bioif-data-model-dev-v1.0.0 version=1.0.0 inputs=11 data_layers=2 model_layers=2 thresholds=6 license_layers_separated=true negative_controls_clean=true resumed=1 target_values_exposed=false
```

## Freeze evidence

- Eleven inputs are checksum-pinned: Silver and Gold-auto manifests, T057 QC,
  T062 modality links, T078 uncertainty, T079 multimodal, T102 negative
  controls, two model configs, and two model-result artifacts.
- Two data layers and two model layers are frozen with six explicit thresholds
  and four dependency-version entries.
- The selected uncertainty policy is `conservative_conformal`; the selected
  multimodal representation is `material_protocol_masked`, with leakage passed
  and missingness masks enabled.
- T102 strict negative controls remain clean with zero critical leakage; T062
  pseudo-pairing is disabled.
- Data/model artifacts are marked analysis-only, configs/cards are redistributable
  metadata, and locked targets are not included. Any mutation is rejected
  without overwrite.

## Acceptance evidence

| Gate | Result |
|---|---|
| Version | `bioif-data-model-dev-v1.0.0` / semantic version `1.0.0` |
| Inputs | 11 checksum-pinned inputs |
| Data/model layers | 2 / 2 |
| Thresholds | 6 frozen thresholds; 4 frozen dependency entries |
| Robustness | T102 `ATTACKS_CLEAN`; critical leaks 0 |
| Licensing | Analysis-only data/model artifacts; redistributable configs/cards; locked targets excluded |
| Immutability | First freeze, byte-stable resume, checksum mutation, and tamper rejection passed |
| Full test suite | 343 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Repository gates | Lockfile, sync, schema, assets, catalog, lockbox, immutable data release, state, compileall, and diff checks passed |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |

## Artifacts

- Schema: `agents/release/freeze_dev.v1.json` (SHA-256 `a822032886d1b5cdb2c2332af2a0c4881cee164cc4c147981f32171753301259`)
- Fixture: `tests/fixtures/release/freeze_dev_fixture.json` (SHA-256 `7e3ce0b25bc68e65ed52c6a8e00fa246ed359b5422065c36e21382b5d0eab979`)
- Workflow and CLI: `src/biointerfaceos/release_freeze_dev.py`, `src/biointerfaceos/cli.py`
- Release directory: `release/dev_data_model/bioif-data-model-dev-v1.0.0/`
- Release manifest SHA-256: `5037a83c862f61a389509a77bda6fe21a945a58b178bed5b81e6f241c99f9be5`
- Data/model card SHA-256: `46bdde074aa4c829f40126b1a2c19e3cfbcbbd3ce2592789b536eb464196de19`
- Freeze manifest SHA-256: `0645c1a5989ae3199c49d2e08caf728ac54bbaf3c4e10b5adb9df02748e8bcc5`
- Freeze receipt SHA-256: `c87d14eebfd44c2189eab8d029fc7141b0b8b209ee2f2a2c29ead54e22a79805`

The next task is T105: draft Paper A benchmark manuscript.
