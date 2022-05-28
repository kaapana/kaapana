FROM local-only/dcmtk-base:3.6.4

LABEL IMAGE="pdf2dcm"
LABEL VERSION="3.6.4"
LABEL CI_IGNORE="False"

COPY files/start.py .

CMD ["python3","-u","/start.py"]
