FROM local-only/base-python-cpu:latest

LABEL IMAGE="airflow"
LABEL VERSION="2.11.0"
LABEL BUILD_IGNORE="False"
LABEL BUILD_LIB_CONTEXT="True"
# This image requires the kaapana/lib directory as a named build context.
# The build script handles this automatically.
# To build manually:
#   docker build --build-context lib=<path-to-kaapana>/lib -t <tag> .

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV DCMDICTPATH=/scripts/dicom.dic
ENV DICT_PATH=/scripts/dicom_tag_dict.json

WORKDIR /kaapana/app

# Copy lib packages from the named build context (kaapana/lib/)
COPY --from=lib kaapana_containers /lib/kaapana_containers
COPY --from=lib task_api /lib/task_api

COPY files/requirements.txt /files/requirements.txt
COPY files/constraints-3.12.txt /files/constraints-3.12.txt
RUN python3 -m pip install apache-airflow[cncf.kubernetes]==2.11.0 -c /files/constraints-3.12.txt
RUN python3 -m pip install --upgrade setuptools pip && pip3 install -r /files/requirements.txt
COPY files/scripts/ /scripts

COPY files/bootstrap.sh /kaapana/app/bootstrap.sh
RUN chmod +x /kaapana/app/bootstrap.sh

COPY files/scheduler_job_runner_2.10.3_adapted.py /opt/venv/lib/python3.12/site-packages/airflow/jobs/scheduler_job_runner.py
COPY files/task_command_2.10.3_adapted.py /opt/venv/lib/python3.12/site-packages/airflow/cli/commands/task_command.py

CMD ["/kaapana/app/bootstrap.sh"]
