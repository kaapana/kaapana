FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Remove default non-root user 1000
RUN userdel -r ubuntu || true

LABEL IMAGE="migration"
LABEL BUILD_IGNORE="False"



# Install required packages: python3, pip, curl, bash, docker CLI
RUN apt-get update && \
    apt-get install -y python3 python3-pip curl bash docker.io && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV KUBE_VERSION="v1.33.0"
# kubectl
RUN curl -LO https://dl.k8s.io/release/${KUBE_VERSION}/bin/linux/amd64/kubectl && chmod +x kubectl && mv ./kubectl /usr/local/bin/kubectl

WORKDIR /kaapana/app

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/migration.py"]
