FROM local-only/base-python-cpu:latest

LABEL IMAGE="pdf2dcm"
LABEL VERSION="3.6.4"
LABEL BUILD_IGNORE="False"

COPY files/start.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
