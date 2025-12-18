FROM local-only/base-python-cpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-model-installer"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/provide_models.py /kaapana/app/provide_models.py
COPY files/requirements.txt /kaapana/app/

RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

CMD ["python3","-u","/kaapana/app/provide_models.py", "-e"]
