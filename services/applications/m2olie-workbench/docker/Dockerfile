FROM local-only/base-python-cpu:latest

LABEL IMAGE="m2olie-workbench"
LABEL VERSION="2023-10-10"
LABEL CI_IGNORE="False"
ENV ELASTIX_VERSION="5.0.0"

RUN mkdir -p /src

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN wget --no-check-certificate https://data.jtfc.de/mitk-elastix-2023_10_27.tar.gz -O /src/elastix.tar.bz
RUN tar -xvf /src/elastix.tar.bz -C /usr/ && rm -rf /src/elastix.tar.bz

WORKDIR /

# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startMITK.sh
RUN ln -s /kaapana/mounted/data /root/Desktop/
WORKDIR /kaapana/mounted/data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/
