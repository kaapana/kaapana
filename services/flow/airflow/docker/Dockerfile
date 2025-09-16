# syntax=docker/dockerfile:1.3-labs

FROM local-only/base-python-cpu:latest

LABEL IMAGE="airflow"
LABEL VERSION="2.10.5"
LABEL BUILD_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV DCMDICTPATH=/scripts/dicom.dic
ENV DICT_PATH=/scripts/dicom_tag_dict.json

WORKDIR /kaapana/app

COPY files/requirements.txt /files/requirements.txt
COPY files/constraints-3.12.txt /files/constraints-3.12.txt
RUN python3 -m pip install apache-airflow[cncf.kubernetes]==2.10.5 -c /files/constraints-3.12.txt
RUN python3 -m pip install --upgrade setuptools pip && pip3 install -r /files/requirements.txt
COPY files/scripts/ /scripts

COPY files/bootstrap.sh /kaapana/app/bootstrap.sh
RUN chmod +x /kaapana/app/bootstrap.sh

ENTRYPOINT ["/kaapana/app/bootstrap.sh"]
