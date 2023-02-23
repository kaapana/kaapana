FROM local-only/base-python-cpu:latest

LABEL IMAGE="debug-container"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    apt-transport-https \
    nmap \
    netcat \
    iputils-ping \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /app/
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY files/flask_headers.py /app/
CMD ["python3","-u","/app/flask_headers.py"]
