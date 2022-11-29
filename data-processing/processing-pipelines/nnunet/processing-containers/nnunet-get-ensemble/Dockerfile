FROM local-only/base-python-alpine:latest

LABEL IMAGE="nnunet-get-ensemble"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

ENV MODELDIR "/models"

COPY files/ensemble_models /tmp/ensemble_models
COPY files/start.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/start.py"]
