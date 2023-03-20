FROM local-only/base-python-cpu:latest

LABEL IMAGE="security-stackrox-install"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

WORKDIR /
   
ENV STACKROX_VERSION="74.0.0"
RUN curl -L https://github.com/stackrox/helm-charts/raw/main/opensource/stackrox-central-services-${STACKROX_VERSION}.tgz -o ./stackrox-central-services.tgz
RUN curl -L https://github.com/stackrox/helm-charts/raw/main/opensource/stackrox-secured-cluster-services-${STACKROX_VERSION}.tgz -o ./stackrox-secured-cluster-services.tgz

ENV KUBE_LATEST_VERSION="v1.23.0"
ENV HELM_VERSION="v3.8.1"
RUN curl https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl
RUN curl https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz | tar -xzO linux-amd64/helm > /usr/local/bin/helm && chmod +x /usr/local/bin/helm

ENV HELM_PATH="/usr/local/bin/helm"
ENV KUBECTL_PATH="kubectl"

COPY files/ ./
RUN chmod +x init.sh

ENTRYPOINT ["/init.sh"]
