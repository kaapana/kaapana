FROM local-only/base-python-cpu:latest

LABEL IMAGE="custom-notify"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/custom-notify.py /kaapana/app/
WORKDIR /kaapana/app/

CMD ["python3","-u","/kaapana/app/custom-notify.py"]