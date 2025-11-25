FROM local-only/base-python-cpu:latest

LABEL IMAGE="update-seginfo"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
