# The scenario suite (profile: eval in compose.yml). This image holds no MISMO
# files: compose mounts the staged DU schema when the suite runs.
# Build context: prototype/ (see compose.yml).

FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS build
ENV UV_PYTHON_DOWNLOADS=0 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY eval/pyproject.toml eval/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.13-slim-trixie
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY eval/pyproject.toml eval/conftest.py ./
COPY eval/support support
COPY eval/scenarios scenarios

# It runs as the host user (compose.yml), who can only write to results/.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTEST_ADDOPTS="-p no:cacheprovider"
USER 1000
ENTRYPOINT ["pytest"]
