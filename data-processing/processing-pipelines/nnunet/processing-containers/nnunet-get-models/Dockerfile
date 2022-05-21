FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="nnunet-get-models"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

ENV MODELDIR "/models"

COPY files/process.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/process.py"]