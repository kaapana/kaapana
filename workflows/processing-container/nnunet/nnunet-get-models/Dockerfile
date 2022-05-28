FROM python:3.9-alpine3.12


LABEL IMAGE="nnunet-get-models"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

ENV MODELDIR "/models"

COPY files/process.py /

CMD ["python3","-u","/process.py"]