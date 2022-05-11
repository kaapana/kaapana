FROM local-only/base-python-cpu:0.1.0

LABEL IMAGE="pdf2dcm"
LABEL VERSION="3.6.4"
LABEL CI_IGNORE="False"

COPY files/start.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/start.py"]
