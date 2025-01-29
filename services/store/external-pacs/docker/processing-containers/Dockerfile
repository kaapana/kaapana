FROM local-only/base-python-cpu:latest

LABEL IMAGE="external-pacs"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

COPY files/external-pacs.py /kaapana/app/
COPY files/CustomHelperDcmWeb.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/external-pacs.py"]