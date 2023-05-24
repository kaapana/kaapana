FROM local-only/no-vnc-base:latest

LABEL IMAGE="m2olie-workbench"
LABEL VERSION="2022.10"
LABEL CI_IGNORE="False"
ENV ELASTIX_VERSION="5.0.0"

WORKDIR /src
RUN mkdir -p /mitk

RUN wget https://github.com/SuperElastix/elastix/releases/download/${ELASTIX_VERSION}/elastix-${ELASTIX_VERSION}-linux.tar.bz2 -O /src/elastix.tar.bz2
RUN tar -xvjf /src/elastix.tar.bz2 -C /usr/ && rm -rf /src/elastix.tar.bz2

RUN wget --no-check-certificate https://data.jtfc.de/mitk-elastix.tar.gz -O /src/mitk-elastix.tar.gz && \
    tar -xzf /src/mitk-elastix.tar.gz --strip 1 -C /mitk/ && rm -rf /src/mitk-elastix.tar.gz

# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startMITK.sh
RUN ln -s /kaapana/mounted/data /root/Desktop/
WORKDIR /kaapana/mounted/data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/
