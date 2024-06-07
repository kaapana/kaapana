FROM local-only/base-python-cpu:latest 

LABEL IMAGE="access-information-point-init"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
COPY files/models.py /kaapana/app/

RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

CMD ["python3", "/kaapana/app/models.py"]