FROM ubuntu:20.04

LABEL IMAGE="airflow"
LABEL VERSION="2.2.5"
LABEL CI_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

WORKDIR /
RUN apt-get update && apt-get install -y \
        wget \
        python3.8 \
        python3.8-dev \
        python3-pip \
        dcmtk \
        curl \
        nano \
        unzip \
        zip \
        # libczmq-dev \
        # libcurlpp-dev \
        # libssl-dev \
        # inetutils-telnet \
        # bind9utils \
        # libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3.8 -m pip install --upgrade pip && python3.8 -m pip install -U setuptools

COPY files/requirements.txt ./
RUN python3.8 -m pip install --no-cache-dir -r requirements.txt --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.2.5/constraints-3.8.txt"

COPY files/scripts/ /scripts

COPY files/bootstrap.sh /bootstrap.sh
RUN chmod +x /bootstrap.sh

COPY files/scheduler_job.py /usr/local/lib/python3.8/dist-packages/airflow/jobs/

ENTRYPOINT ["./bootstrap.sh"]
