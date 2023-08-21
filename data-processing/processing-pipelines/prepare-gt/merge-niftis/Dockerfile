FROM local-only/base-python-cpu:latest

LABEL IMAGE="merge-niftis"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

COPY files/*.py /

CMD ["python3","-u","/start.py"]