FROM python:3.9-alpine

LABEL IMAGE="federated-backend"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app

RUN apk add gcc musl-dev libffi-dev openssl-dev python3-dev

COPY files/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]