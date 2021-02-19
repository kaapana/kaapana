FROM local-only/no-vnc-base:0.1.0

LABEL IMAGE="mitk-workbench"
LABEL VERSION="2021.02-vdev"
LABEL CI_IGNORE="False"

WORKDIR /src
RUN mkdir -p /mitk
ADD https://www.mitk.org/download/kaapana/workbench/MITK-v2021.02-linux-x86_64.tar.gz /src/mitk.tar.gz
RUN tar -xzf /src/mitk.tar.gz --strip 1 -C /mitk/ && rm -rf /src/mitk.tar.gz

# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startMITK.sh
RUN ln -s /data /root/Desktop/
WORKDIR /data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/
