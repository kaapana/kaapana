# FROM python:3.9-alpine3.12
FROM python:3.9

LABEL IMAGE="kaapana-backend"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y python3-dev build-essential

# TODO: COPY ../../datamodel /datamodel is outside of build context
# COPY datamodel /datamodel
# RUN pip install /datamodel

# COPY files/requirements.txt requirements.txt
COPY files/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# COPY files/ ./
COPY files/ ./

ENV FLASK_APP run.py
EXPOSE 5000
CMD ./boot.sh
