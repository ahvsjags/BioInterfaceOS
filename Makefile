.PHONY: env check paper-a paper-b paper-c-prelock freeze-prelock

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

paper-a:
	.venv/bin/biointerfaceos paper-a

paper-b:
	.venv/bin/biointerfaceos paper-b

paper-c-prelock:
	.venv/bin/biointerfaceos paper-c-prelock

freeze-prelock:
	.venv/bin/biointerfaceos release freeze-prelock --strict
