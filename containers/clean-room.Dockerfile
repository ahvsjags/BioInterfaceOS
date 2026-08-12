FROM python:3.11-slim

WORKDIR /workspace/BioInterfaceOS
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY agents ./agents
COPY tests ./tests
COPY Makefile ./Makefile

# The image is intended for an offline build context with uv and the locked
# wheel cache supplied by the caller. No network access is required or allowed.
RUN python -m pip install --no-index --find-links=/wheelhouse uv==0.8.13 \
    && uv sync --frozen --offline --no-dev

COPY containers/clean-room-run.sh ./containers/clean-room-run.sh
ENTRYPOINT ["bash", "containers/clean-room-run.sh"]
