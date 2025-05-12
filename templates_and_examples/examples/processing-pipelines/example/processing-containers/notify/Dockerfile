FROM local-only/base-python-cpu:latest

LABEL IMAGE="example-notify"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/example-notify.py /kaapana/app/
WORKDIR /kaapana/app/

CMD ["python3","-u","/kaapana/app/example-notify.py"]