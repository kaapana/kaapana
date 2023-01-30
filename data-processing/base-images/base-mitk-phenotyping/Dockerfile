FROM local-only/base-python-cpu:latest

ARG DEBIAN_FRONTEND=noninteractive

LABEL REGISTRY="local-only"
LABEL IMAGE="base-mitk-phenotyping"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

WORKDIR /app

COPY files/requirements.system /app/
RUN apt-get update -y && cat /app/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /app/
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt && rm /app/requirements.txt 

RUN wget --no-check-certificate https://www.mitk.org/download/kaapana/phenotyping/MITK-v2021.02-linux-x86_64.tar.gz -O /app/mitk.tar.gz \
    && tar -xzf /app/mitk.tar.gz --strip 1 -C /app/ && rm -rf /app/mitk.tar.gz

CMD ["echo","Do not use this container directly - only as base-image!"]
