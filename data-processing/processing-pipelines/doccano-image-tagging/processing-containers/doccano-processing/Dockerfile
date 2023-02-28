FROM local-only/base-python-cpu:latest

LABEL IMAGE="doccano-processing"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/trigger_job.py"]