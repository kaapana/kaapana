FROM ubuntu:20.10

ENV http_proxy http://www-int2.dkfz-heidelberg.de:80
ENV https_proxy http://www-int2.dkfz-heidelberg.de:80

LABEL IMAGE="airflow"
LABEL VERSION="2.2.5"
LABEL CI_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

WORKDIR /

#RUN apt-get update -y
#RUN apt install software-properties-common -y
#RUN add-apt-repository ppa:deadsnakes/ppa -y


RUN cp /etc/apt/sources.list /etc/apt/sources.list.bak 

# replace the links with the archive address
RUN sed -i -re 's/([a-z]{2}.)?archive.ubuntu.com|security.ubuntu.com/old-releases.ubuntu.com/g' /etc/apt/sources.list

# run update again
RUN apt-get update &&  apt-get dist-upgrade

RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        python3.8 \
        python3.8-dev \
        python3-pip \
        dcmtk \
        curl \
        nano \
        unzip \
        zip \
        openssh-client \
        vim \
        skopeo \
        # libczmq-dev \
        # libcurlpp-dev \
        # libssl-dev \
        # inetutils-telnet \
        # bind9utils \
        # libpq-dev \
    && rm -rf /var/lib/apt/lists/*

#RUN apt install python3.8-distutils -y

RUN python3.8 -m pip install --upgrade pip && python3.8 -m pip install -U setuptools

#RUN pip3 install setuptools

COPY files/requirements.txt ./
RUN python3.8 -m pip install --no-cache-dir -r requirements.txt --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.2.5/constraints-3.8.txt"

COPY files/scripts/ /scripts

RUN ansible-galaxy collection install openstack.cloud
RUN ansible-galaxy collection install community.docker

COPY files/bootstrap.sh /bootstrap.sh
RUN chmod +x /bootstrap.sh

COPY files/scheduler_job.py /usr/local/lib/python3.8/dist-packages/airflow/jobs/

RUN mkdir -p /root/.ssh
# COPY files/tfda_iso.pem  /root/.ssh/tfda_iso.pem
# RUN chmod 600 /root/.ssh/tfda_iso.pem
# SKOPEO Installation
#RUN echo "deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_20.04/ /" |  tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
#RUN curl -L https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_20.04/Release.key |  apt-key add -
#RUN  apt-get update
#RUN  apt-get -y install skopeo

#sudo apt-get -y update
#sudo apt-get -y install skopeo

ENTRYPOINT ["./bootstrap.sh"]
