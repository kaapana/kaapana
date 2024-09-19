FROM local-only/base-mitk:latest

LABEL IMAGE="mitk-fileconverter"
LABEL VERSION="2024-08-08"
LABEL BUILD_IGNORE="False"


COPY files/mitk_fileconverter.py /kaapana/app/
CMD ["python3","-u", "/kaapana/app/mitk_fileconverter.py"]
