FROM local-only/base-python-cpu:latest

LABEL IMAGE="airflow"
LABEL VERSION="2.10.3"
LABEL BUILD_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

WORKDIR /kaapana/app

COPY files/requirements.txt /files/requirements.txt
COPY files/constraints-3.12.txt /files/constraints-3.12.txt
RUN python -m pip install --upgrade setuptools pip && pip3 install -c /files/constraints-3.12.txt -r /files/requirements.txt

COPY files/scripts/ /scripts

COPY files/bootstrap.sh /kaapana/app/bootstrap.sh
RUN chmod +x /kaapana/app/bootstrap.sh

COPY files/scheduler_job_runner_2.10.3_adapted.py /opt/venv/lib/python3.12/site-packages/airflow/jobs/scheduler_job_runner.py
COPY files/task_command_2.10.3_adapted.py /opt/venv/lib/python3.12/site-packages/airflow/cli/commands/task_command.py

ENTRYPOINT ["/kaapana/app/bootstrap.sh"]
