FROM local-only/base-python-cpu:latest

LABEL IMAGE="zip-unzip"
LABEL VERSION="3.0.0"
LABEL CI_IGNORE="False"

COPY files/ /app/

CMD ["python3","-u","/app/process.py"]
