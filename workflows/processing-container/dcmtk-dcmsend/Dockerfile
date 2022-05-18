FROM local-only/base-dcmtk:3.6.4

LABEL IMAGE="dcmsend"
LABEL VERSION="3.6.4"
LABEL CI_IGNORE="False"

COPY files/start.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/start.py"]
