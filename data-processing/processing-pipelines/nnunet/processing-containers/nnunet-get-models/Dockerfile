FROM local-only/base-python-alpine:latest

LABEL IMAGE="nnunet-get-models"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

ENV MODELDIR "/models"

COPY files/process.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/process.py"]