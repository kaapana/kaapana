FROM local-only/base-python-cpu:latest

LABEL IMAGE="svs-to-dicom"
LABEL BUILD_IGNORE="False"

RUN pip3 install --no-cache-dir pydicom wsidicomizer

COPY processing-container.json /

WORKDIR /home/kaapana
COPY files/svs_to_dicom.py /home/kaapana/
