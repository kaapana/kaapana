FROM python:3.9-alpine3.12 as build-stage

LABEL IMAGE="doccano-backend"
LABEL VERSION="sha-0489118"
LABEL CI_IGNORE="False"

RUN apk add --no-cache git

RUN git clone https://github.com/doccano/doccano.git doccano && cd doccano && git checkout 0489118f92084d85b30a95a8b306636dfae38ff9

FROM python:3.8.6-slim-buster

CMD ["python3"]

WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=build-stage /doccano/backend /backend/
COPY --from=build-stage /doccano/Pipfile* /backend/

# hadolint ignore=DL3013
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    netcat=1.* \
    libpq-dev=11.* \
    unixodbc-dev=2.* \
    g++=4:* \
 && pip install --no-cache-dir pipenv==2020.11.15 \
 && pipenv install --system --deploy \
 && pip uninstall -y pipenv virtualenv-clone virtualenv \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build-stage /doccano/tools/ /opt/bin/
RUN mkdir -p /backend/staticfiles \
  && mkdir -p /backend/client/dist/static \
  && mkdir -p /backend/media

VOLUME /backend/staticfiles

ENTRYPOINT [ "/opt/bin/prod-django.sh" ]

