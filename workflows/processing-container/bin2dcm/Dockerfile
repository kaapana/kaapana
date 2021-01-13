FROM local-only/dcmtk-base:3.6.4-vdev

LABEL IMAGE="bin2dcm"
LABEL VERSION="3.6.4-vdev"
LABEL CI_IGNORE="False"

COPY files/template.xml .
COPY files/start.py .

CMD ["python3","-u","/start.py"]
