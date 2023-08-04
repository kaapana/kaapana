FROM local-only/base-python-cpu:latest

LABEL IMAGE="kaapana-persistence-backend"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /app/
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY files/ /app
RUN chmod +x /app/boot.sh

ENTRYPOINT ["/app/boot.sh"]