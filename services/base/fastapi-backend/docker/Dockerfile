FROM python:3.8

LABEL IMAGE="fastapi-backend"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y python3-dev build-essential

COPY files/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

ENV FLASK_APP run.py


EXPOSE 5000

ENTRYPOINT ["./boot.sh"]