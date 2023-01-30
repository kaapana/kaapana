FROM dorowu/ubuntu-desktop-lxde-vnc:focal

LABEL REGISTRY="local-only"
LABEL IMAGE="no-vnc-base"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

WORKDIR /app

RUN sed -i 's#mirror://mirrors.ubuntu.com/mirrors.txt#http://archive.ubuntu.com/ubuntu/#' /etc/apt/sources.list;

RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -

COPY files/requirements.system /app/
RUN apt-get update -y && cat /app/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

COPY files/startup.sh /app/startup.sh

RUN chmod +x /app/startup.sh
