FROM ubuntu:20.04

LABEL IMAGE="airflow"
LABEL VERSION="1.10.15-vdev"
LABEL CI_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
        wget \
        python3-dev \
        python3-pip \
        libczmq-dev \
        libcurlpp-dev \
        curl \
        libssl-dev \
        git \
        inetutils-telnet \
        bind9utils \
        zip \
        unzip \
        nano \
        curl \
        dcmtk \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip
RUN pip3 install -U setuptools

WORKDIR /
COPY files/requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

COPY files/scripts/ /scripts
COPY files/bootstrap.sh /bootstrap.sh
RUN chmod +x /bootstrap.sh

COPY files/scheduler_job.py /usr/local/lib/python3.8/dist-packages/airflow/jobs/

ENTRYPOINT ["./bootstrap.sh"]
