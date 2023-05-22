FROM local-only/base-python-cpu:latest

LABEL IMAGE="debug-container"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    apt-transport-https \
    nmap \
    netcat \
    iputils-ping \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/flask_headers.py /kaapana/app/
CMD ["python3","-u","/kaapana/app/flask_headers.py"]
