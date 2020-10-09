FROM python:3.6-alpine

LABEL REGISTRY="local"
LABEL IMAGE="dag-installer"
LABEL VERSION="1.0-vdev"
LABEL CI_IGNORE="False"

RUN pip install requests==2.24.0

COPY files/run.py run.py

CMD ["python3","-u","/run.py"]