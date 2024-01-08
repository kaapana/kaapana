FROM local-only/base-python-cpu:latest

LABEL IMAGE="merge-masks"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
