FROM quay.io/podman/stable:v4.4.1 

LABEL IMAGE="podman"
LABEL VERSION="4.4.1"

ENV CONTAINERD_SOCK="/root/containerd.sock"

WORKDIR /kaapana/app

RUN curl -L https://github.com/containerd/containerd/releases/download/v1.5.13/containerd-1.5.13-linux-amd64.tar.gz -o containerd.tar.gz
RUN tar -xf containerd.tar.gz
RUN cp bin/ctr /usr/local/bin/ctr && chmod +x /usr/local/bin/ctr
RUN rm -rf containerd* bin/

RUN curl -L https://code-server.dev/install.sh -o install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

COPY files/kaapana.sh /kaapana/app/
RUN cat /kaapana/app/kaapana.sh >> ~/.bashrc