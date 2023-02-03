FROM local-only/base-python-cpu:latest

LABEL IMAGE="tcia-download"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apt-get update && apt-get install -y xvfb

COPY files/requirements.txt /kaapanasrc/requirements.txt
RUN pip3 install --upgrade pip && pip install -r /kaapanasrc/requirements.txt

COPY files/* /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/tcia_download.py"]
