FROM local-only/base-python-cpu:latest

LABEL IMAGE="simple-execution"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/start.py"]