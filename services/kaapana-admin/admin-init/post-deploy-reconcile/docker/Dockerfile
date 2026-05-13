FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

LABEL IMAGE="post-deploy-reconcile"
LABEL BUILD_IGNORE="False"

RUN apt-get update && \
    apt-get install -y bash curl postgresql-client && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV KUBE_VERSION="v1.33.0"
RUN curl -LO https://dl.k8s.io/release/${KUBE_VERSION}/bin/linux/amd64/kubectl && \
    chmod +x kubectl && mv ./kubectl /usr/local/bin/kubectl

WORKDIR /kaapana/app

COPY files/reconcile.sh /kaapana/app/reconcile.sh
RUN chmod +x /kaapana/app/reconcile.sh

CMD ["/kaapana/app/reconcile.sh"]
