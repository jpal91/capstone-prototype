gen-schema:
    rm -rf ./mismo/src/mismo/generated
    cd ./mismo/src && uv run --package mismo -- \
        xsdata generate ../schema/ReferenceModel_v3.4.0_B324/Combined/MISMO_3.4.0_B324.xsd \
        --package mismo.generated
