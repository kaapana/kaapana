FROM local-only/base-mitk-phenotyping:latest

LABEL IMAGE="mitk-radiomics"
LABEL VERSION="2021-02-18"
LABEL BUILD_IGNORE="False"

WORKDIR /
ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR radiomics

COPY files/radiomics.sh /kaapana/app/

CMD ["/bin/bash", "/kaapana/app/radiomics.sh"]
