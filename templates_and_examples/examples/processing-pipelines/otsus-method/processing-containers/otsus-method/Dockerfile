FROM ubuntu:20.04

LABEL IMAGE="otsus-method"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

RUN apt update
RUN apt install -y python3 python3-pip

RUN python3 -m pip install SimpleITK

COPY files/ /

CMD ["python3","-u","otsus_method.py"]