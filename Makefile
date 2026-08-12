.PHONY: env check paper-a paper-b paper-c-prelock freeze-prelock lockbox-evaluate lockbox-audit publication-render reproduce-clean claim-audit project-accept

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

lockbox-evaluate:
	.venv/bin/biointerfaceos lockbox evaluate --release FROZEN_DEV --once

lockbox-audit:
	.venv/bin/biointerfaceos lockbox audit-results --strict

publication-render:
	.venv/bin/biointerfaceos publication render --strict

reproduce-clean:
	.venv/bin/biointerfaceos reproduce-clean --strict

claim-audit:
	.venv/bin/biointerfaceos claim audit-manuscripts --strict

project-accept:
	.venv/bin/biointerfaceos project accept --strict
