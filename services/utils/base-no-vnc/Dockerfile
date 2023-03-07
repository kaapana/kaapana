FROM dorowu/ubuntu-desktop-lxde-vnc:focal

LABEL REGISTRY="local-only"
LABEL IMAGE="no-vnc-base"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

RUN sed -i 's#mirror://mirrors.ubuntu.com/mirrors.txt#http://archive.ubuntu.com/ubuntu/#' /etc/apt/sources.list;

RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -

COPY files/requirements.system /kaapana/app/
RUN apt-get update -y && cat /kaapana/app/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
    
RUN pip install --no-cache-dir \
    # Security fix for CVE-2021-33503
    urllib3==1.26.5 \
    # Security fix for CVE-2022-40898
    wheel==0.38.1 \
    # Security fix for CVE-2023-25577
    Werkzeug==2.2.3 \
    # Werkzeug 2.0.0+ breaks Flask
    Flask==2.2.3 \
    Jinja2==3.1.2

COPY files/startup.sh /startup.sh

RUN chmod +x /startup.sh
