schema := "./mismo/schema/ReferenceModel_v3.4.0_B324"
du := schema / "Fannie Mae DU Schema Files updated 080825"
staged := "./mismo/schema/staged"

# Generate the bindings from the base MISMO schema. xsdata can't resolve the
# DU extension schemas' no-namespace references, so the DU wrapper is used
# for validation only (see stage-schema).
gen-schema:
    rm -rf ./mismo/src/mismo/generated
    cd ./mismo/src && uv run --package mismo -- \
        xsdata generate ../schema/ReferenceModel_v3.4.0_B324/Combined/MISMO_3.4.0_B324.xsd \
        --package mismo.generated

# Copy everything DU_Wrapper_3.4.0_B324.xsd references into one folder,
# because its relative schemaLocations expect them side by side.
# Copies, not symlinks: some tools resolve a symlink to its original folder.
stage-schema:
    rm -rf {{staged}}
    mkdir -p {{staged}}
    cp {{schema}}/Combined/*.xsd \
        {{schema}}/MISMODataTypesB324.xsd \
        {{schema}}/MISMOEnumeratedTypesB324.xsd \
        {{schema}}/MISMOExtensionDetailsB324.xsd \
        "{{du}}"/*.xsd \
        {{staged}}/
