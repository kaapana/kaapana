FROM local-only/base-python-alpine:0.1.0

LABEL REGISTRY="local-only"
LABEL IMAGE="charts-manager"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/run.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/run.py"]