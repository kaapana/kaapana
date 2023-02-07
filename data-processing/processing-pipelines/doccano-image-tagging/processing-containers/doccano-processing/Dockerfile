FROM local-only/base-python-cpu:latest

LABEL IMAGE="doccano-processing"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /app/

CMD ["python3","-u","/app/trigger_job.py"]