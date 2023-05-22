FROM docker.io/alpine/git:2.36.3 as build-stage

LABEL IMAGE="doccano-backend"
LABEL VERSION="sha-0489118"
LABEL CI_IGNORE="False"

WORKDIR /

# Reduce caching layers
# hadolint ignore=DL3003
RUN git clone https://github.com/doccano/doccano.git doccano && cd doccano && git checkout 0489118f92084d85b30a95a8b306636dfae38ff9

FROM docker.io/python:3.8.16-slim-buster

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
 && pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt --no-cache-dir pipenv==2020.11.15 \
 && pipenv install --system --deploy \
 && pip uninstall -y pipenv virtualenv-clone virtualenv \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* 

 # Security fixes
 RUN pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt --no-cache-dir \ 
      # Security fix for CVE-2022-40898
      wheel==0.38.1 \
      # Security fix for CVE-2022-40897
      setuptools==65.5.1 \
      # Security fix for CVE-2022-21797
      joblib==1.2.0 \
      # Security fix for CVE-2023-0286
      cryptography==39.0.1 \
      # Security fix for CVE-2021-23727
      celery==5.2.2 \
      # Security fix for CVE-2022-28346
      Django==3.2.18 \
      # Security fix for CVE-2022-29217
      PyJWT==2.6.0 
 
COPY --from=build-stage /doccano/tools/ /opt/bin/
RUN mkdir -p /backend/staticfiles \
  && mkdir -p /backend/client/dist/static \
  && mkdir -p /backend/media

VOLUME /backend/staticfiles

ENTRYPOINT [ "/opt/bin/prod-django.sh" ]

