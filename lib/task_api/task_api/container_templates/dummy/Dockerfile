FROM ubuntu:24.04

LABEL IMAGE="dummy"
LABEL BUILD_IGNORE="False"

RUN userdel -r ubuntu

# Install apt packages
WORKDIR /app
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3-pip \
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*


COPY processing-container.json /

WORKDIR /home/dummy
COPY files/upstream.py /home/dummy/
COPY files/downstream.py /home/dummy/
