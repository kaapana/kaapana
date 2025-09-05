datamodel-codegen \
 --input schemas/ \
 --input-file-type jsonschema \
 --output generated_models/ \
 --target-python-version 3.12 \
 --output-model-type pydantic_v2.BaseModel \
 --use-annotate \
 --disable-timestamp \
 --use-schema-description