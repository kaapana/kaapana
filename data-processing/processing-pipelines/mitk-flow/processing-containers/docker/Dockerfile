FROM local-only/base-desktop:latest

LABEL IMAGE="mitk-flow"
LABEL VERSION="2023.12"
LABEL BUILD_IGNORE="False"

RUN mkdir -p /mitk-flow \
    && wget https://www.mitk.org/download/kaapana/flowbench/MITK-122321bb-linux-x86_64.tar.gz -O /mitk-flow/mitk.tar.gz \
    && tar -xzf /mitk-flow/mitk.tar.gz --strip 1 -C /mitk-flow/ \
    && rm -rf /mitk-flow/mitk.tar.gz

COPY files/startMITKFlow.sh /mitk/startMITKFlow.sh

RUN ln -s /data /home/$USER/Desktop/
WORKDIR /data

COPY files/supervisord-mitk-flowbench.conf /etc/supervisor/conf.d/