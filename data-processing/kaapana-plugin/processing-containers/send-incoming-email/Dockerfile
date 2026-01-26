FROM local-only/base-python-cpu:latest

LABEL IMAGE="send-incoming-email"
LABEL VERSION="1.0.0"
LABEL BUILD_IGNORE="False"

COPY files/start.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
