FROM local-only/base-python-cpu:latest

LABEL IMAGE="pyradiomics"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apt-get update

COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt
COPY files/pyradiomics.py /kaapanasrc/

WORKDIR /kaapanasrc/
CMD ["python3","-u","/kaapanasrc/pyradiomics.py"]
