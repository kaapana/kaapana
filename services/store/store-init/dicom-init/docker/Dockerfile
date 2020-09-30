FROM dktk-jip-registry.dkfz.de/kaapana-public/dicom_phantom:1.0 as files

LABEL IMAGE="dicom-init"
LABEL VERSION="0.9-vdev"
LABEL CI_IGNORE="False"

FROM ubuntu:20.04

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY --from=files /Winfried_phantom.zip /example/Winfried_phantom.zip

RUN apt-get update && apt-get install -y \
    dcmtk \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install pydicom \
    requests \
    elasticsearch

COPY files/full_index_dicom /test_dicom
COPY files/start.py /start.py

CMD ["python3","-u","/start.py"]