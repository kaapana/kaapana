FROM local-only/base-mitk:latest

LABEL IMAGE="mitk-radiomics"
LABEL VERSION="2021-02-18"
LABEL BUILD_IGNORE="False"

WORKDIR /
ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR radiomics
ENV QT_QPA_PLATFORM offscreen
ENV QT_QPA_PLATFORM_PLUGIN_PATH /kaapana/app/bin/plugins/platforms/libqxcb.so

COPY files/radiomics.sh /kaapana/app/
COPY files/requirements.txt /kaapana/app/


RUN apt-get update -y && apt-get install -y --no-install-recommends xvfb
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN python -m pip install -c /constraints.txt -r /kaapana/app/requirements.txt


CMD ["/bin/bash", "/kaapana/app/radiomics.sh"]
