FROM local-only/base-python-cpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-charts-manager"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

COPY files/run.py /

CMD ["python3","-u","/run.py"]