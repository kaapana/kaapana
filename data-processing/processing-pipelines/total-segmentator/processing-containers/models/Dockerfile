FROM local-only/base-model-installer:latest

LABEL IMAGE="get-totalsegmentator-models"
LABEL BUILD_IGNORE="False"

ARG include_model_weights="false"

COPY files/model_lookup.json /model_lookup.json

RUN python3 -u /kaapana/app/provide_models.py --all=$include_model_weights