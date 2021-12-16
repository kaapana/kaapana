FROM registry.hzdr.de/andre.klein/multiple-myeloma-image-analysis/mitk-radiomics:2021-02-18-vdev
LABEL IMAGE="mitk-radiomics-myeloma"
LABEL VERSION="2021-02-18-vdev"
LABEL CI_IGNORE="False"

WORKDIR /
ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR radiomics

COPY files/radiomics.sh /

CMD ["/bin/bash", "/radiomics.sh"]
