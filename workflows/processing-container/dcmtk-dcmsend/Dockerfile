FROM local-only/dcmtk-base:3.6.4-vdev

LABEL IMAGE="dcmsend"
LABEL VERSION="3.6.4-vdev"
LABEL CI_IGNORE="False"

COPY files/start.py .

CMD ["python3","-u","/start.py"]
