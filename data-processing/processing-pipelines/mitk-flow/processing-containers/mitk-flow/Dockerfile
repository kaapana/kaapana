FROM local-only/no-vnc-base:latest

LABEL IMAGE="mitk-flow"
LABEL VERSION="2022.10"
LABEL CI_IGNORE="False"

WORKDIR /src
RUN mkdir -p /mitk

RUN wget https://www.mitk.org/download/kaapana/flowbench/MITK-v2022.10-linux-x86_64.tar.gz -O /src/mitk.tar.gz \
    && tar -xzf /src/mitk.tar.gz --strip 1 -C /mitk/ && rm -rf /src/mitk.tar.gz

# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /home/mitk/Desktop/
RUN chmod 0777 /home/mitk/Desktop/startMITK.sh
RUN ln -s /data /home/mitk/Desktop/
WORKDIR /data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/