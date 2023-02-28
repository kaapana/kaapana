FROM local-only/base-python-cpu:latest

LABEL IMAGE="hello-backend"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

<<<<<<< HEAD
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
=======
COPY files/requirements.system ./
RUN apt-get update -y && cat /kaapana/app/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
>>>>>>> b0d47d1c823a51dd3af874a59ed61ecd4d468b94

COPY files/requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

ENV FLASK_APP run.py

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]

