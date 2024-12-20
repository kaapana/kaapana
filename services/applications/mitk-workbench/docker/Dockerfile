FROM local-only/base-mitk:latest AS mitk-image
FROM local-only/base-desktop:latest

LABEL IMAGE="mitk-workbench"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

COPY --from=mitk-image /kaapana/app/ /mitk/

RUN ln -s /kaapana/minio /home/$USER/Desktop/data
WORKDIR /kaapana/minio

COPY files/startMITK.sh /mitk/
COPY files/supervisord-mitk.conf /etc/supervisor/conf.d/

