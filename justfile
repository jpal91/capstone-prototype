schema := "./mismo/schema/ReferenceModel_v3.4.0_B324"
du := schema / "Fannie Mae DU Schema Files updated 080825"
staged := "./mismo/schema/staged"
combined := schema / "Combined/MISMO_3.4.0_B324.xsd"
missing := "is missing. The MISMO schema is license-restricted and not in the repository; see mismo/README.md."

# Generate the bindings from the base MISMO schema. xsdata can't resolve the
# DU extension schemas' no-namespace references, so the DU wrapper is used
# for validation only (see stage-schema).
gen-schema:
    @test -f {{ combined }} || { echo "{{ combined }} {{ missing }}" >&2; exit 1; }
    rm -rf ./mismo/src/mismo/generated
    cd ./mismo/src && uv run --package mismo -- \
        xsdata generate ../schema/ReferenceModel_v3.4.0_B324/Combined/MISMO_3.4.0_B324.xsd \
        --package mismo.generated

# Stage what DU_Wrapper_3.4.0_B324.xsd needs into one folder (its relative
# schemaLocations expect the files side by side):
# - Combined/: the single-file MISMO schema. The wrapper's xsd:redefine only
#   finds the types it redefines in this version, not the split one.
# - three of the split part files from the top level, because the ULAD/DU
#   extension schemas import MISMODataTypesB324.xsd (which includes the other two).
#   The top-level MISMO_3.4.0_B324.xsd is deliberately not copied.
# Copies, not symlinks: some tools resolve a symlink to its original folder.
stage-schema:
    @test -f {{ combined }} || { echo "{{ combined }} {{ missing }}" >&2; exit 1; }
    @test -d "{{ du }}" || { echo "{{ du }} {{ missing }}" >&2; exit 1; }
    rm -rf {{ staged }}
    mkdir -p {{ staged }}
    cp {{ schema }}/Combined/*.xsd \
        {{ schema }}/MISMODataTypesB324.xsd \
        {{ schema }}/MISMOEnumeratedTypesB324.xsd \
        {{ schema }}/MISMOExtensionDetailsB324.xsd \
        "{{ du }}"/*.xsd \
        {{ staged }}/

api-dev:
    uv run --package core fastapi dev core/src/core/app.py

# Regenerate the portal's typed core client from core's OpenAPI spec. Run after
# changing core's routes or models, and commit both files: the portal image
# builds without Python or the MISMO bindings that importing core needs.
gen-api:
    mkdir -p ./portal/app/lib/core
    uv run --package core python -c "import json; from core.app import app; \
        open('./portal/app/lib/core/openapi.json', 'w').write(json.dumps(app.openapi(), indent=2) + '\n')"
    cd portal && pnpm exec openapi-typescript app/lib/core/openapi.json -o app/lib/core/schema.d.ts

# Start the docker services
docker-up:
    docker compose up -d

# Stop docker services
docker-down:
    docker compose down -v

# Restart container
docker-restart: docker-down docker-up
