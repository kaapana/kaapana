FROM local-only/base-python-cpu:latest

LABEL IMAGE="otsus-method"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apt update
RUN apt install -y python3 python3-pip

RUN python3 -m pip install SimpleITK==2.2.1 nibabel==5.0.0 pynrrd==1.0.0 matplotlib==3.6.3

COPY files/ /kaapanasrc/
WORKDIR /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/otsus_method.py"]