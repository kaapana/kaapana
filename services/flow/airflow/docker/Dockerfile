FROM local-only/base-python-cpu:latest

LABEL IMAGE="airflow"
LABEL VERSION="2.2.5"
LABEL CI_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

WORKDIR /kaapana/app

COPY files/requirements.txt ./
COPY files/constraints-3.9.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt --constraint 'constraints-3.9.txt'

COPY files/scripts/ /scripts

COPY files/bootstrap.sh /kaapana/app/bootstrap.sh
RUN chmod +x /kaapana/app/bootstrap.sh

COPY files/scheduler_job.py /usr/local/lib/python3.9/site-packages/airflow/jobs/

ENTRYPOINT ["/kaapana/app/bootstrap.sh"]
