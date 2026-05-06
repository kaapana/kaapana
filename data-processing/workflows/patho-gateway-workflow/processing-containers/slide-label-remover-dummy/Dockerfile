FROM local-only/base-python-cpu:latest

LABEL IMAGE="slide-label-remover-dummy"
LABEL BUILD_IGNORE="False"

RUN pip3 install --no-cache-dir pydicom

COPY processing-container.json /

WORKDIR /kaapana/app
COPY files/pass_through.py /kaapana/app/
