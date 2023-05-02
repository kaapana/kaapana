FROM local-only/base-python-cpu:latest

LABEL IMAGE="nnunet-model-management"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

COPY files/start.py /

CMD ["python3","-u","/start.py"]