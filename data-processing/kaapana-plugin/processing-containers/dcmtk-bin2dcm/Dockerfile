FROM local-only/base-python-cpu:latest

LABEL IMAGE="bin2dcm"
LABEL VERSION="3.6.4"
LABEL BUILD_IGNORE="False"

COPY files/template.xml /kaapana/app/
COPY files/start.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
