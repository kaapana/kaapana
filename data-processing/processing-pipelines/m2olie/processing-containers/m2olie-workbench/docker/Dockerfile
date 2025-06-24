FROM local-only/base-desktop:latest

LABEL IMAGE="m2olie-workbench"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"
ENV ELASTIX_VERSION="5.0.0"

RUN mkdir -p /src

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /m2olie \
    && wget --no-check-certificate https://data.jtfc.de/mitk-elastix-20231031_22-04_linux-x86_64.tar.gz  -O /m2olie/elastix.tar.gz \
    && tar -xzf /m2olie/elastix.tar.gz --strip 1 -C /m2olie/ \
    && rm -rf /m2olie/elastix.tar.gz

COPY files/startMITK.sh /m2olie/

RUN ln -s /data /home/$USER/Desktop/
WORKDIR /data


COPY files/supervisord-m2olie.conf /etc/supervisor/conf.d/

