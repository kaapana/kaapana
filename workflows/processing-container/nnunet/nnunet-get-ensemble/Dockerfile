FROM python:3.9-alpine3.12

LABEL IMAGE="nnunet-get-ensemble"
LABEL VERSION="0.1.1-vdev"
LABEL CI_IGNORE="False"

ENV MODELDIR "/models"

COPY files/ensemble_models /tmp/ensemble_models
COPY files/start.py /

CMD ["python3","-u","/start.py"]