FROM docker.io/alpine/git:2.43.0 as build-stage

LABEL IMAGE="doccano-backend"
LABEL VERSION="sha-0489118"
LABEL BUILD_IGNORE="False"

WORKDIR /

# Reduce caching layers
# hadolint ignore=DL3003
RUN git clone https://github.com/doccano/doccano.git doccano && cd doccano && git checkout 0489118f92084d85b30a95a8b306636dfae38ff9

FROM docker.io/python:3.8.18-slim

CMD ["python3"]

WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=build-stage /doccano/backend /backend/
COPY --from=build-stage /doccano/Pipfile* /backend/

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  netcat=1.* \
  libpq-dev=11.* \
  unixodbc-dev=2.* \
  g++=4:* \
  && pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir pipenv==2020.11.15 \
  && pipenv install --system --deploy \
  && pip uninstall -y pipenv virtualenv-clone virtualenv \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* 

RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir \ 
  wheel==0.42.0 \
  setuptools==69.0.3 \
  joblib==1.3.2 \
  cryptography==42.0.5 \
  celery==5.3.6 \
  Django==3.2.18 \
  PyJWT==2.8.0

COPY --from=build-stage /doccano/tools/ /opt/bin/
RUN mkdir -p /backend/staticfiles \
  && mkdir -p /backend/client/dist/static \
  && mkdir -p /backend/media

VOLUME /backend/staticfiles

ENTRYPOINT [ "/opt/bin/prod-django.sh" ]

