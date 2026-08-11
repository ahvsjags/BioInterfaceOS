# T008 — Storage accounting and quota guard

Implement deterministic repository-local storage accounting, duplicate content detection,
quota checks, raw-data deletion protection, and read-only transient cleanup discovery.

The implementation is in `src/biointerfaceos/storage.py`, configured by
`config/storage.yaml`, and exposed through `biointerfaceos storage audit --strict`.
Focused acceptance coverage is in `tests/test_storage.py`.
