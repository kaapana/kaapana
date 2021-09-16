FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

LABEL IMAGE="dicom-init"
LABEL VERSION="0.1.1-vdev"
LABEL CI_IGNORE="False"

RUN apt-get update && apt-get install -y \
    dcmtk \
    python3 \
    python3-pip \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install pydicom \
    requests \
    elasticsearch

RUN curl --header "DEPLOY-TOKEN: EaexsV_q2BKG8BeurRT8" --output /test-dicoms.zip "https://gitlab.hzdr.de/api/v4/projects/2521/packages/generic/test-data/0.0.3/init-dicoms.zip" \
    && mkdir -p /dicom_test_data && unzip /test-dicoms.zip -d /dicom_test_data && rm -rf test-dicoms.zip

COPY files/start.py /start.py

CMD ["python3","-u","/start.py"]