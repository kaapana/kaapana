FROM local-only/base-python-cpu:latest

LABEL IMAGE="scanparam2json"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/scanparam2json.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/scanparam2json.py"]