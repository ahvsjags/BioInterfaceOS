.PHONY: env check

BIOINTERFACEOS_UV ?= uv
BIOINTERFACEOS_PYTHON ?= 3.11

env:
	$(BIOINTERFACEOS_UV) sync --frozen --python $(BIOINTERFACEOS_PYTHON)
	@echo "Environment ready. Activate with: source .venv/bin/activate"

check:
	$(BIOINTERFACEOS_UV) run --frozen ruff check src tests
	$(BIOINTERFACEOS_UV) run --frozen ruff format --check src tests
	$(BIOINTERFACEOS_UV) run --frozen mypy
	$(BIOINTERFACEOS_UV) run --frozen pytest
