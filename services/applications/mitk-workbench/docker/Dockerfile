FROM local-only/base-mitk:latest  as base-mitk
FROM local-only/no-vnc-base:latest

LABEL IMAGE="mitk-workbench"
LABEL VERSION="2023.12"
LABEL BUILD_IGNORE="False"

WORKDIR /src
RUN mkdir -p /mitk

COPY --from=base-mitk /kaapana/app/ /mitk/


# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startMITK.sh
RUN ln -s /kaapana/minio /root/Desktop/
WORKDIR /kaapana/minio

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/

