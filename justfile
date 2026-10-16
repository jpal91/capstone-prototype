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

# Stage what DU_Wrapper_3.4.0_B324.xsd needs into one folder (its relative
# schemaLocations expect the files side by side):
# - Combined/: the single-file MISMO schema. The wrapper's xsd:redefine only
#   finds the types it redefines in this version, not the split one.
# - three of the split part files from the top level, because the ULAD/DU
#   extension schemas import MISMODataTypesB324.xsd (which includes the other two).
#   The top-level MISMO_3.4.0_B324.xsd is deliberately not copied.
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
