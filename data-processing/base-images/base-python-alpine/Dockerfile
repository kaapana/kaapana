FROM python:3.9.12-alpine3.15

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-alpine"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apk update && apk add --no-cache \ 
    # bash \
    # ca-certificates \
    # curl \
    gcc \
    # git \
    # jpeg-dev \
    libc-dev \
    libffi-dev \
    musl-dev \
    # openssh \
    # openssl-dev \
    # postgresql-dev \
    python3-dev \
    # zlib-dev \
    # npm \
    && rm -rf /var/cache/apk/*


COPY files/requirements.txt /root/
RUN python -m pip install --upgrade pip && pip3 install -r /root/requirements.txt

# Codeserver
# Resources:
# https://github.com/martinussuherman/alpine-code-server
# https://coder.com/docs/code-server/latest/install#standalone-releases
ENV VERSION=4.2.0
RUN apk update && apk add --no-cache \
    npm \
    curl \
    gcompat \
    && rm -rf /var/cache/apk/*

RUN mkdir -p ~/.local/lib ~/.local/bin && curl -fL https://github.com/coder/code-server/releases/download/v$VERSION/code-server-$VERSION-linux-amd64.tar.gz \
  | tar -C ~/.local/lib -xz && \
  mv ~/.local/lib/code-server-$VERSION-linux-amd64 ~/.local/lib/code-server-$VERSION
COPY files/code-server /usr/bin/
RUN chmod +x /usr/bin/code-server
RUN code-server --install-extension ms-python.python

# Jupyterlab
RUN jupyter notebook --generate-config \
 && sed -i "s/^.*NotebookApp.token.*$/c.NotebookApp.token = ''/g" /root/.jupyter/jupyter_notebook_config.py
COPY files/jupyterlab.sh /