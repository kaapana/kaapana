FROM local-only/base-python-cpu:0.1.0

LABEL IMAGE="pyradiomics"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

RUN apt-get update && apt-get install -y xvfb

COPY files/pyradiomics.py /kaapanasrc/
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

WORKDIR /kaapanasrc/
CMD ["python3","-u","/kaapanasrc/pyradiomics.py"]
