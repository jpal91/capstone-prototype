# Images built from this contain the license-restricted MISMO schema and
# generated bindings: never push them to a public registry.
# Build context: prototype/ (see compose.yml).

FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS build
ENV UV_PYTHON_DOWNLOADS=0 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Third-party dependencies first, so this layer is cached until uv.lock changes.
COPY pyproject.toml uv.lock ./
COPY core/pyproject.toml core/
COPY mismo/pyproject.toml mismo/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package core --no-install-workspace

COPY core/src core/src
COPY mismo/src mismo/src
COPY mismo/schema/ReferenceModel_v3.4.0_B324 mismo/schema/ReferenceModel_v3.4.0_B324

# Generate the bindings and stage the DU wrapper (same steps as `just
# gen-schema` and `just stage-schema`), before the non-editable install
# copies mismo into the venv.
ARG SCHEMA=mismo/schema/ReferenceModel_v3.4.0_B324
RUN test -f "$SCHEMA/Combined/MISMO_3.4.0_B324.xsd" || { \
    echo "$SCHEMA is missing. The MISMO schema is license-restricted and not in the repository; see mismo/README.md." >&2; exit 1; } \
    && rm -rf mismo/src/mismo/generated \
    && cd mismo/src \
    && /app/.venv/bin/xsdata generate \
    "/app/$SCHEMA/Combined/MISMO_3.4.0_B324.xsd" --package mismo.generated \
    && cd /app \
    && mkdir -p staged \
    && cp "$SCHEMA"/Combined/*.xsd \
    "$SCHEMA"/MISMODataTypesB324.xsd \
    "$SCHEMA"/MISMOEnumeratedTypesB324.xsd \
    "$SCHEMA"/MISMOExtensionDetailsB324.xsd \
    "$SCHEMA/Fannie Mae DU Schema Files updated 080825"/*.xsd \
    staged/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package core --no-editable

FROM python:3.13-slim-trixie
RUN useradd --system --no-create-home app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/staged /app/schema

ENV PATH="/app/.venv/bin:$PATH" \
    MISMO_SCHEMA=/app/schema/DU_Wrapper_3.4.0_B324.xsd \
    HOST=0.0.0.0
USER app
EXPOSE 8000
CMD ["core"]
