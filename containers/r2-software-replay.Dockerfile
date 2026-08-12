FROM python:3.11-slim

WORKDIR /workspace/BioInterfaceOS

# This recipe is intentionally offline: callers supply a locked wheelhouse and
# invoke Docker with --network=none. librsvg provides the deterministic R2
# SVG-to-PNG/PDF conversion used by the protocol-figure replay.
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY docs ./docs
COPY containers/r2-software-replay-run.sh ./containers/r2-software-replay-run.sh
COPY AGENTS.md LICENSE NOTICE CITATION.cff ./
RUN apt-get update && apt-get install -y --no-install-recommends librsvg2-bin \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-index --find-links=/wheelhouse uv==0.8.13 \
    && uv sync --frozen --offline --no-dev

ENTRYPOINT ["bash", "containers/r2-software-replay-run.sh"]
