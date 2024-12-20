FROM local-only/base-python-cpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-installer"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/run.py /kaapana/app/run.py

CMD ["python3","-u","/kaapana/app/run.py"]
