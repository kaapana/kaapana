# FROM python:3.9-alpine3.12
FROM python:3.9

LABEL IMAGE="kaapana-datamodel"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

WORKDIR /

RUN apt-get update \
    && apt-get install --no-install-recommends -y python3-dev build-essential



# COPY files/requirements.txt requirements.txt
COPY files/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# TODO: COPY ../../datamodel /datamodel is outside of build context
COPY files/datamodel ./datamodel
RUN pip install -e ./datamodel

# COPY files/ ./
COPY files/app ./app
COPY files/boot.sh ./
RUN chmod +x ./boot.sh
EXPOSE 5000
ENTRYPOINT ["./boot.sh"]