FROM local-only/base-python-cpu:latest

LABEL IMAGE="trigger-ansible-playbook"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

## TODO: Following is hard-coded proxy, which needs to change
ENV http_proxy http://www-int2.dkfz-heidelberg.de:80
ENV https_proxy http://www-int2.dkfz-heidelberg.de:80

WORKDIR /kaapana/app

RUN mkdir -p /root/.ssh
RUN touch /root/.ssh/config
RUN echo "StrictHostKeyChecking=accept-new" > /root/.ssh/config

## TODO Remove Skopeo from this image if not needed
RUN apt-get update -q -y &&  apt-get dist-upgrade -q -y
RUN apt-get update -q -y && apt-get install -y --no-install-recommends \
        openssh-client \
        vim \
        skopeo \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt

RUN ansible-galaxy collection install openstack.cloud:==1.8.0
RUN ansible-galaxy collection install community.docker
RUN ansible-galaxy collection install community.libvirt:==1.2.0

COPY files/ansible-playbooks /kaapana/app/ansible-playbooks
COPY files/run_ansible_playbook.py /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/run_ansible_playbook.py"]
