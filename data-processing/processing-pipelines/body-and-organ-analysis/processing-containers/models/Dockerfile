FROM local-only/base-model-installer:latest

LABEL IMAGE="get-body-and-organ-analysis-models"
LABEL VERSION="0.1.3"
LABEL BUILD_IGNORE="False"

ARG include_model_weights="false"

COPY files/model_lookup.json /model_lookup.json

RUN python3 -u /kaapana/app/provide_models.py --all=$include_model_weights
