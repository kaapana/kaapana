FROM local-only/no-vnc-base:0.1.0

LABEL IMAGE="m2aia-workbench"
LABEL VERSION="2021.07-vdev"
LABEL CI_IGNORE="False"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libqt5charts5-dev \
    libopenslide-dev \
    && rm -rf /var/lib/apt/lists/*


ARG M2AIA_BASE_VERSION="2021.07.00"
ENV M2AIA_BASE_VERSION=$M2AIA_BASE_VERSION

ARG M2AIA_FEATURE_VERSION="2021.07.01"
ENV M2AIA_FEATURE_VERSION=$M2AIA_FEATURE_VERSION

ARG ELASTIX_VERSION="5.0.0"
ENV ELASTIX_VERSION=$ELASTIX_VERSION

RUN mkdir -p /src /m2aia
RUN wget https://github.com/SuperElastix/elastix/releases/download/${ELASTIX_VERSION}/elastix-${ELASTIX_VERSION}-linux.tar.bz2 -O /src/elastix.tar.bz2
RUN tar -xvjf /src/elastix.tar.bz2 -C /usr/ && rm -rf /src/elastix.tar.bz2

RUN wget https://github.com/jtfcordes/M2aia/releases/download/v${M2AIA_BASE_VERSION}/M2aia-${M2AIA_FEATURE_VERSION}-linux-x86_64.tar.gz -O /src/m2aia.tar.gz
RUN tar -xzf /src/m2aia.tar.gz --strip 1 -C /m2aia/ && rm -rf /src/m2aia.tar.gz

# Application start definition, here a shell script is used to start the application
COPY files/startM2aia.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startM2aia.sh
RUN ln -s /data /root/Desktop/
WORKDIR /data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/