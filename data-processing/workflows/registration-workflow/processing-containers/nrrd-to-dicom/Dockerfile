FROM local-only/base-python-cpu:latest

LABEL IMAGE="nrrd-to-dicom"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /kaapana/app

COPY files/convert-nrrd-to-dicom.sh /kaapana/app/
COPY files/nrrd_to_dicom.py /kaapana/app/