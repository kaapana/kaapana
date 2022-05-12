FROM nikolaik/python-nodejs:python3.9-nodejs14-alpine

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-alpine"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apk update && apk add --no-cache \ 
    bash \
    ca-certificates \
    curl \
    gcc \
    git \
    jpeg-dev \
    libc-dev \
    libffi-dev \
    musl-dev \
    openssh \
    openssl-dev \
    postgresql-dev \
    python3-dev \
    zlib-dev \
    && rm -rf /var/lib/apt/lists/*

# Common Python packages
RUN python -m pip install --upgrade pip
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

# Code server
# Resources:
# https://github.com/martinussuherman/alpine-code-server
# https://coder.com/docs/code-server/latest/install#standalone-releases
ENV VERSION=4.2.0
RUN apk update && apk add --no-cache gcompat && rm -rf /var/lib/apt/lists/*
RUN mkdir -p ~/.local/lib ~/.local/bin
RUN curl -fL https://github.com/coder/code-server/releases/download/v$VERSION/code-server-$VERSION-linux-amd64.tar.gz \
  | tar -C ~/.local/lib -xz && \
  mv ~/.local/lib/code-server-$VERSION-linux-amd64 ~/.local/lib/code-server-$VERSION
COPY files/code-server /usr/bin/
RUN chmod +x /usr/bin/code-server
RUN code-server --install-extension ms-python.python

WORKDIR /kaapanasrc