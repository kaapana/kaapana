FROM local-only/no-vnc-base:latest

LABEL IMAGE="mitk-workbench"
LABEL VERSION="2022.10"
LABEL CI_IGNORE="False"

WORKDIR /src
RUN mkdir -p /mitk


RUN wget https://www.mitk.org/download/kaapana/workbench/MITK-v2022.10-linux-x86_64.tar.gz -O /src/mitk.tar.gz && \
    tar -xzf /src/mitk.tar.gz --strip 1 -C /mitk/ && rm -rf /src/mitk.tar.gz

# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startMITK.sh
RUN ln -s /kaapana/mounted/mitk-data /root/Desktop/
WORKDIR /kaapana/mounted/mitk-data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/
