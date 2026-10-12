FROM local-only/base-python-cpu:latest

LABEL IMAGE="trident-dicom-utils"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/requirements.txt
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/*.py /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/start.py"]
