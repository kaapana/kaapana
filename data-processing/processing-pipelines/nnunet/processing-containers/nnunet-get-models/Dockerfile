FROM local-only/base-python-cpu:latest

LABEL IMAGE="nnunet-get-models"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

ENV MODELDIR "/models"

COPY files/process.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/process.py"]