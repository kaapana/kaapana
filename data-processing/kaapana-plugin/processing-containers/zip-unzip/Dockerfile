FROM local-only/base-python-cpu:latest

LABEL IMAGE="zip-unzip"
LABEL VERSION="3.0.0"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/process.py"]
