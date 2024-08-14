FROM local-only/base-python-gpu:latest

LABEL IMAGE="edk"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

# install skopeo for copying containers from/to registries https://github.com/containers/skopeo
RUN apt-get update -y && apt-get -y install skopeo

# install helm
ENV HELM_VERSION="v3.14.0"
RUN curl https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz | tar -xzO linux-amd64/helm > /usr/local/bin/helm && chmod +x /usr/local/bin/helm

RUN mkdir -p /kaapana/app/kaapana
RUN mkdir -p /kaapana/app/dag
RUN mkdir -p /kaapana/app/utils

COPY files/utils /kaapana/app/utils
COPY files/*.sh /kaapana/app
COPY files/README.md /kaapana/app

RUN pip install -r /kaapana/app/utils/requirements.txt

RUN chmod +x /kaapana/app/*.sh

CMD ["/usr/bin/bash", "init.sh"]