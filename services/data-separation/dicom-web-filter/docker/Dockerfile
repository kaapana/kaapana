FROM local-only/base-python-cpu:latest

LABEL IMAGE="dicom-web-filter"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

RUN apt-get update

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/ /kaapana/app
RUN chmod +x /kaapana/app/boot.sh

CMD ["/bin/sh", "/kaapana/app/boot.sh"]