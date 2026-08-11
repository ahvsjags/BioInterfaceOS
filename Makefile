.PHONY: env

BIOINTERFACEOS_UV ?= uv
BIOINTERFACEOS_PYTHON ?= 3.11

env:
	$(BIOINTERFACEOS_UV) sync --frozen --python $(BIOINTERFACEOS_PYTHON)
	@echo "Environment ready. Activate with: source .venv/bin/activate"
