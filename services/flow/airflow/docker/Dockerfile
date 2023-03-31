FROM local-only/base-python-cpu:latest

LABEL IMAGE="airflow"
LABEL VERSION="2.5.2"
LABEL CI_IGNORE="False"

ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

ENV DCMDICTPATH /scripts/dicom.dic
ENV DICT_PATH /scripts/dicom_tag_dict.json

# Create a group "kaapana" and user "kaapana" with minimal rights
RUN addgroup --gid 1000 kaapana && \
    adduser --no-create-home --uid 1000 --gid 1000 --shell /bin/sh --disabled-login --disabled-password kaapana

WORKDIR /kaapana/app

COPY files/requirements.txt ./
COPY files/constraints-3.9.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt --constraint 'constraints-3.9.txt'

COPY files/scripts/ /scripts

COPY files/bootstrap.sh /kaapana/app/bootstrap.sh
RUN chmod +x /kaapana/app/bootstrap.sh

COPY files/scheduler_job.py /usr/local/lib/python3.9/site-packages/airflow/jobs/

# Create the required directory and set permissions
RUN mkdir -p /kaapana/mounted/workflows/ && \
    chown -R 1000:1000 /kaapana/mounted/workflows/ && \
    # Set "kaapana" as the owner of the /kaapana/app directory
    chown -R 1000:1000 /kaapana/app

# Switch to the "kaapana" user for security reasons
USER kaapana

ENTRYPOINT ["/kaapana/app/bootstrap.sh"]
