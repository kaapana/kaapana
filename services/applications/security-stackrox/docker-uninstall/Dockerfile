FROM local-only/base-python-cpu:latest

LABEL IMAGE="security-stackrox-uninstall"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

WORKDIR /

ENV KUBE_LATEST_VERSION="v1.23.0"
RUN curl https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl

ENV HELM_PATH="/usr/local/bin/helm"
ENV KUBECTL_PATH="kubectl"

COPY files/ ./
RUN chmod +x init.sh

ENTRYPOINT ["/init.sh"]
