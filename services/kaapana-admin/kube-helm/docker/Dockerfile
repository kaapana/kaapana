FROM local-only/base-python-cpu:latest

LABEL IMAGE="kube-helm"
LABEL VERSION="0.1.4"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

# Set versions for cli tools
ENV KUBE_VERSION="v1.31.2"
ENV HELM_VERSION="v3.16.3"
ENV CONTAINERD_VERSION="1.7.12"

# Install kubectl and helm cli tools
RUN curl -LO https://dl.k8s.io/release/${KUBE_VERSION}/bin/linux/amd64/kubectl && chmod +x kubectl && mv ./kubectl /usr/local/bin/kubectl
RUN curl https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz | tar -xzO linux-amd64/helm > /usr/local/bin/helm && chmod +x /usr/local/bin/helm
RUN mkdir /config && chmod g+rwx /config    

RUN apt-get update

# Install containerd cli tool
RUN curl -L https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz -o containerd.tar.gz
RUN tar -xf containerd.tar.gz
RUN cp bin/ctr /usr/local/bin/ctr && chmod +x /usr/local/bin/ctr
RUN rm -rf containerd* bin/

# Install pip packages
COPY files/requirements.txt /kaapana/app/
RUN pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt -r /kaapana/app/requirements.txt

# Copy all files for containers
COPY files/backend /kaapana/app/backend
COPY files/update-collections-chart /root/collections/update-collections-chart
COPY files/pull-docker-chart /root/helpers/pull-docker-chart

# Package helper charts via `helm package`
RUN /usr/local/bin/helm package /root/collections/update-collections-chart -d /root/collections
RUN /usr/local/bin/helm package /root/helpers/pull-docker-chart -d /root/helpers

# Set paths and other env vars
ENV HELM_PATH="/usr/local/bin/helm"
ENV KUBECTL_PATH="kubectl"
ENV HELM_EXTENSIONS_CACHE="/kaapana/mounted/extensions"
ENV HELM_PLATFORMS_CACHE="/kaapana/mounted/platforms"
ENV LOG_LEVEL="info"
ENV RECENT_UPDATE_CACHE="true"
ENV CONTAINERD_SOCK="/kaapana/mounted/containerd.sock"

EXPOSE 5000

CMD ["/bin/sh", "/kaapana/app/backend/boot.sh"]
