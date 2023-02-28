FROM local-only/base-python-cpu:latest

LABEL IMAGE="debug-container"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

<<<<<<< HEAD
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    apt-transport-https \
    nmap \
    netcat \
    iputils-ping \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*
=======
COPY files/requirements.system /kaapana/app/
RUN apt-get update -y && cat /kaapana/app/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
>>>>>>> b0d47d1c823a51dd3af874a59ed61ecd4d468b94

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/flask_headers.py /kaapana/app/
CMD ["python3","-u","/kaapana/app/flask_headers.py"]
