FROM local-only/base-python-cpu:latest

LABEL IMAGE="dicom-pseudonymizer"
LABEL BUILD_IGNORE="False"

RUN pip3 install --no-cache-dir pydicom

COPY processing-container.json /

WORKDIR /kaapana/app
COPY files/pseudonymize.py /kaapana/app/
