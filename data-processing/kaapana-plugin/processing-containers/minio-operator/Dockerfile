FROM local-only/base-python-cpu:latest

LABEL IMAGE="minio-operator"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/start.py /kaapana/app/

CMD ["python","-u","/kaapana/app/start.py"]