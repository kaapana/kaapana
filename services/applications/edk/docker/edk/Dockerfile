FROM local-only/base-python-gpu:latest

LABEL IMAGE="edk"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

# install skopeo for copying containers from/to registries https://github.com/containers/skopeo
RUN apt-get update -y && apt-get -y install skopeo

# install helm
ENV HELM_VERSION="v3.21.2"
# Download with retries/resume to a file instead of piping into tar: transient
# connection resets have failed release builds here, and the pipe discarded
# curl's exit status (no pipefail in the default build shell).
RUN curl -sS -L -f -C - --retry 20 --retry-all-errors --retry-delay 10 \
        -o /tmp/helm.tar.gz "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" \
    && tar -xzOf /tmp/helm.tar.gz linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm \
    && rm /tmp/helm.tar.gz

RUN mkdir -p /kaapana/app/kaapana
RUN mkdir -p /kaapana/app/dag
RUN mkdir -p /kaapana/app/utils

COPY files/utils /kaapana/app/utils
COPY files/*.sh /kaapana/app/
COPY files/README.md /kaapana/app/

RUN pip install -r /kaapana/app/utils/requirements.txt

RUN chmod +x /kaapana/app/*.sh

CMD ["/usr/bin/bash", "init.sh"]