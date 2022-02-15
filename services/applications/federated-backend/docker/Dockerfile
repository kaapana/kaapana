FROM python:3.9-alpine

LABEL IMAGE="federated-backend-fast-api"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app

# RUN HTTPS_PROXY="http://www-int2.dkfz-heidelberg.de:80" apk add gcc postgresql-dev python3-dev musl-dev
RUN HTTPS_PROXY="http://www-int2.dkfz-heidelberg.de:80" apk add gcc musl-dev libffi-dev openssl-dev python3-dev
# RUN HTTPS_PROXY="http://www-int2.dkfz-heidelberg.de:80" apk update && HTTPS_PROXY="http://www-int2.dkfz-heidelberg.de:80" apk add gcc postgresql-dev python3-dev musl-dev
# RUN pip install  --proxy=http://www-int2.dkfz-heidelberg.de:80 psycopg2-binary

# ENV HTTP_PROXY="http://www-int2.dkfz-heidelberg.de:80"
# ENV HTTPS_PROXY="http://www-int2.dkfz-heidelberg.de:80"

COPY files/requirements.txt requirements.txt
RUN pip install --proxy=http://www-int2.dkfz-heidelberg.de:80 -r requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

ENV FLASK_APP run.py


EXPOSE 5000

ENTRYPOINT ["./boot.sh"]