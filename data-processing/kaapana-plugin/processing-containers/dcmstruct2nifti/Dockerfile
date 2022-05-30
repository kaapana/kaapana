FROM python:3.9-slim

LABEL IMAGE="dcmstruct2nifti"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/start.py /kaapanasrc/
CMD ["python3","-u","/kaapanasrc/start.py"]
