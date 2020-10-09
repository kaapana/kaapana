FROM python:3.9-alpine3.12

LABEL REGISTRY="local"
LABEL IMAGE="dag-installer"
LABEL VERSION="1.0-vdev"
LABEL CI_IGNORE="False"

RUN pip install requests==2.24.0

COPY files/run.py run.py

CMD ["python3","-u","/run.py"]