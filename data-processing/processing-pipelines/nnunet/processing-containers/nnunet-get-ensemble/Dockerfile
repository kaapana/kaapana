FROM local-only/base-python-cpu:latest

LABEL IMAGE="nnunet-get-ensemble"
LABEL VERSION="0.1.1"
LABEL BUILD_IGNORE="False"

ENV MODELDIR "/models"

COPY files/ensemble_models /tmp/ensemble_models
COPY files/start.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
