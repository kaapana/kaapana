FROM local-only/base-python-cpu:latest

LABEL IMAGE="dcmodify"
LABEL VERSION="3.6.4"
LABEL CI_IGNORE="False"

COPY files/start.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
