FROM local-only/base-python-alpine:latest

LABEL IMAGE="hello-backend"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apk update && apk add postgresql-dev \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY files/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

ENV FLASK_APP run.py

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]