FROM local-only/base-python-cpu:latest

LABEL IMAGE="otsus-method"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apt update
RUN apt install -y python3 python3-pip

RUN python3 -m pip install SimpleITK

COPY files/ /kaapanasrc/
WORKDIR /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/otsus_method.py"]