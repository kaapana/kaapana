FROM ubuntu:20.04

LABEL IMAGE="airflow"
LABEL VERSION="2.2.2"
LABEL CI_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
        wget \
        python3.8-dev \
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
RUN pip3 install --no-cache-dir -r requirements.txt --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.2.2/constraints-3.8.txt"

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

COPY files/scripts/ /scripts
COPY files/bootstrap.sh /bootstrap.sh
RUN chmod +x /bootstrap.sh

#COPY files/scheduler_job.py /usr/local/lib/python3.8/dist-packages/airflow/jobs/

# RUN apt-get -y install openssh-client
# RUN ssh-keygen -q -t rsa -N '' -f /kaapana

RUN mkdir -p /root/.ssh
COPY files/tfda_iso.pem  /root/.ssh/tfda_iso.pem
RUN chmod 600 /root/.ssh/tfda_iso.pem

# RUN mkdir -p /root/tfda_platform
# COPY files/server_installation.sh /root/tfda_platform/server_installation.sh
# COPY files/install_platform.sh /root/tfda_platform/install_platform.sh

ENTRYPOINT ["./bootstrap.sh"]
