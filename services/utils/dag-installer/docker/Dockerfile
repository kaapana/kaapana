FROM python:3.9-alpine3.12

LABEL REGISTRY="local-only"
LABEL IMAGE="dag-installer"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

RUN rm /tmp/tmpwgocbik2cacert.pem
RUN pip install requests==2.27.1
COPY files/run.py /run.py
CMD ["python3","-u","/run.py"]
