# T003 Python environment report

## Reproducible environment

- Recorded: 2026-08-11 UTC
- Environment manager: `uv 0.12.1 (x86_64-unknown-linux-gnu)`
- Interpreter: `CPython 3.11.15`
- Virtual environment: repository-local, ignored `.venv`
- Project package: editable `biointerfaceos 0.1.0`
- Runtime dependencies: none
- Lockfile: `uv.lock`, format version 1, revision 3, Python constraint `==3.11.*`
- Lockfile SHA-256: `1a0983851f8aa9c7b5995edd430faa4b157174ca187291ef08f0e5f83c680b4a`
- Frozen package listing: `-e file:///ibex/user/xup0a/BioInterfaceOS`

`pyproject.toml` constrains the supported interpreter to `>=3.11,<3.12` and pins the build backend requirement to `hatchling==1.27.0`. The lock records only the editable project because the T003 core has no runtime dependencies.

## Creation and activation

From the repository root:

```bash
make env
source .venv/bin/activate
python -m biointerfaceos --version
```

`make env` executes `uv sync --frozen --python 3.11`; it reuses the existing `.venv` when present and prints the activation instruction. The activated interpreter must report Python 3.11.x.

## Validation evidence

All successful commands below exited 0:

| Command | Exit | Observed result |
|---|---:|---|
| `make env` | 0 | `uv 0.12.1`, CPython 3.11.15, editable `biointerfaceos==0.1.0` synchronized |
| `source .venv/bin/activate && make env && python -m biointerfaceos --version` | 0 | `0.1.0` |
| activated `python --version` | 0 | `Python 3.11.15` |
| `UV_OFFLINE=true .venv/bin/python -I -c "import biointerfaceos; print(biointerfaceos.__version__)"` | 0 | `0.1.0` |
| `.venv/bin/python -m compileall -q src/biointerfaceos` | 0 | no output |
| `uv lock --check` | 0 | lockfile current |
| `UV_OFFLINE=true uv sync --frozen --python 3.11` | 0 | frozen offline synchronization succeeded |
| `.venv/bin/python -m unittest discover` | 0 | 0 tests run |

The final pre-commit verification also ran `git diff --check` and checked that every staged path was inside this repository and belonged to T003 or its task/state/report records.

## Limitations

This is deliberately the minimal T003 environment. `pytest`, `ruff`, and `mypy` were not installed, and their module commands exited 1 with `ModuleNotFoundError`; they did not pass and were not added as T003 dependencies. Standard-library unittest discovery succeeded but found 0 tests. T004 and later CLI, data, modeling, GPU, and optional development dependencies are not implemented or installed here.
