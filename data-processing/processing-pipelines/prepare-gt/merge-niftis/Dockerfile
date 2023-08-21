FROM local-only/base-mitk-phenotyping:latest

LABEL IMAGE="merge-niftis"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

COPY files/start.py /

CMD ["python3","-u","/start.py"]