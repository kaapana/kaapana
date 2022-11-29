#FROM python:3.9-alpine
FROM ubuntu:20.04

LABEL IMAGE="kaapana-backend"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app

# RUN apk update && apk add gcc musl-dev libffi-dev openssl-dev python3-dev build-base && rm -rf /var/cache/apk/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]