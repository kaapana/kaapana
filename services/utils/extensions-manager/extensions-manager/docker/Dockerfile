FROM python:3.9-alpine3.12

LABEL REGISTRY="local-only"
LABEL IMAGE="extensions-manager"
LABEL VERSION="0.1.0-vdev"
LABEL CI_IGNORE="False"

COPY files/run.py run.py

CMD ["python3","-u","/run.py"]