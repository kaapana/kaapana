FROM local-only/base-python-cpu:latest

LABEL IMAGE="airflow"
LABEL VERSION="2.2.5"
LABEL CI_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

WORKDIR /app

COPY files/requirements.txt ./
RUN python3.8 -m pip install --no-cache-dir -r requirements.txt --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.5.1/constraints-3.8.txt"

COPY files/scripts/ /scripts

COPY files/bootstrap.sh /app/bootstrap.sh
RUN chmod +x /app/bootstrap.sh

COPY files/scheduler_job.py /usr/local/lib/python3.9/dist-packages/airflow/jobs/

ENTRYPOINT ["/app/bootstrap.sh"]
