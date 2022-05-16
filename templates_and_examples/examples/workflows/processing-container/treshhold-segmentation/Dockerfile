FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="treshhold-segmentation"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /
RUN pip install -r requirements.txt
COPY files/process.py /


CMD ["python3","-u","/process.py"]