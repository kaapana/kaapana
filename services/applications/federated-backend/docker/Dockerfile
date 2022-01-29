FROM python:3.8-alpine

LABEL IMAGE="federated-backend"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app

# RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
# RUN pip install psycopg2

ENV HTTP_PROXY="http://www-int2.dkfz-heidelberg.de:80"
ENV HTTPS_PROXY="http://www-int2.dkfz-heidelberg.de:80"

COPY files/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

ENV FLASK_APP run.py

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]