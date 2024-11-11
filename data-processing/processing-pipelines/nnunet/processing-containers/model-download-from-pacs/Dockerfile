FROM local-only/base-python-cpu:latest

LABEL IMAGE="nnunet-model-download-from-pacs"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/download_from_pacs.py /kaapana/app

CMD ["python3","-u","/kaapana/app/download_from_pacs.py"]