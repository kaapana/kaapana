FROM local-only/base-python-cpu:latest

LABEL IMAGE="airflow"
LABEL VERSION="2.10.3"
LABEL BUILD_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

WORKDIR /kaapana/app

COPY files/requirements.txt /files/requirements.txt
RUN python -m pip install --upgrade setuptools pip && pip3 install -c https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.12.txt -r /files/requirements.txt

COPY files/scripts/ /scripts

COPY files/bootstrap.sh /kaapana/app/bootstrap.sh
RUN chmod +x /kaapana/app/bootstrap.sh

COPY files/scheduler_job_runner.py /usr/local/lib/python3.10/dist-packages/airflow/jobs/
COPY files/task_command.py /usr/local/lib/python3.10/dist-packages/airflow/cli/commands/

ENTRYPOINT ["/kaapana/app/bootstrap.sh"]
