FROM local-only/base-python-cpu:latest

LABEL IMAGE="nrrd-to-dicom"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /

WORKDIR /home/kaapana

COPY files/convert-nrrd-to-dicom.sh /home/kaapana/
COPY files/nrrd_to_dicom.py /home/kaapana/