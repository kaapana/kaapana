FROM local-only/base-mitk:latest AS mitk-image
FROM local-only/no-vnc-base:latest

LABEL IMAGE="mitk-workbench"
LABEL VERSION="2023.12"
LABEL BUILD_IGNORE="False"


RUN mkdir -p /mitk
RUN mkdir  -p /home/mitk/Desktop/
RUN ln -s /kaapana/minio /home/mitk/Desktop/

# Create a user "mitk" with a home directory
RUN useradd -u 1000 -ms /bin/bash mitk

WORKDIR /home/mitk

COPY --from=mitk-image /kaapana/app/ /mitk/

COPY files/startMITK.sh /home/mitk/Desktop/

RUN chown -R mitk /home/mitk/Desktop/
RUN chmod +x /home/mitk/Desktop/startMITK.sh
# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/

