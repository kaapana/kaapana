FROM local-only/base-python-cpu:latest

LABEL IMAGE="trigger-ansible-playbook"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

ARG http_proxy
ARG https_proxy
ENV http_proxy=$http_proxy
ENV https_proxy=$https_proxy

WORKDIR /kaapana/app

RUN mkdir -p /root/.ssh
RUN touch /root/.ssh/known_hosts
RUN touch /root/.ssh/config
RUN echo "StrictHostKeyChecking=accept-new" > /root/.ssh/config

RUN apt-get update -q -y &&  apt-get dist-upgrade -q -y
RUN apt-get update -q -y && apt-get install -y --no-install-recommends \
    openssh-client \
    vim \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y python3-dev
COPY files/requirements.txt /
RUN  pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /requirements.txt

RUN ansible-galaxy collection install openstack.cloud:==1.8.0
RUN ansible-galaxy collection install community.docker
RUN ansible-galaxy collection install community.libvirt:==1.2.0

COPY files/ansible-playbooks /kaapana/app/ansible-playbooks
COPY files/run_ansible_playbook.py /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/run_ansible_playbook.py"]
