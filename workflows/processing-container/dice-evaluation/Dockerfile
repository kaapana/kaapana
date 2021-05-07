FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

LABEL IMAGE="dice-evaluation"
LABEL VERSION="0.1.0-vdev"
LABEL CI_IGNORE="False"

WORKDIR /
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/start.py /
CMD ["python3","-u","/start.py"]
