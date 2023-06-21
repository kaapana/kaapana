FROM local-only/base-python-cpu:latest

LABEL IMAGE="pre-and-post-etl"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

ARG http_proxy
ARG https_proxy

ENV http_proxy=$http_proxy
ENV https_proxy=$https_proxy

WORKDIR /kaapana/app

# RUN mkdir -p /root/.ssh

## TODO Remove Skopeo from this image if not needed
RUN apt-get update -q -y &&  apt-get dist-upgrade -q -y
RUN apt-get update -q -y && apt-get install -y --no-install-recommends \
        openssh-client \
        vim \
        skopeo \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt

COPY files/pre_and_post_etl.py /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/pre_and_post_etl.py"]
