FROM local-only/base-python-cpu:latest

LABEL IMAGE="kube-helm"
LABEL VERSION="0.1.4"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

ENV KUBE_LATEST_VERSION="v1.29.1"
ENV HELM_VERSION="v3.14.0"

RUN curl https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl
RUN curl https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz | tar -xzO linux-amd64/helm > /usr/local/bin/helm && chmod +x /usr/local/bin/helm
RUN chmod g+rwx /root && mkdir /config && chmod g+rwx /config    

# Install containerd
RUN apt-get update

# Install ctr
RUN curl -L https://github.com/containerd/containerd/releases/download/v1.7.12/containerd-1.7.12-linux-amd64.tar.gz -o containerd.tar.gz
RUN tar -xf containerd.tar.gz
RUN cp bin/ctr /usr/local/bin/ctr && chmod +x /usr/local/bin/ctr
RUN rm -rf containerd* bin/

COPY files/requirements.txt /kaapana/app/
RUN pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /kaapana/app/requirements.txt

COPY files/backend /kaapana/app/backend

COPY files/update-collections-chart /root/collections/update-collections-chart
RUN /usr/local/bin/helm package /root/collections/update-collections-chart -d /root/collections
COPY files/pull-docker-chart /root/helpers/pull-docker-chart
RUN /usr/local/bin/helm package /root/helpers/pull-docker-chart -d /root/helpers

ENV HELM_PATH "/usr/local/bin/helm"
ENV KUBECTL_PATH "kubectl"
ENV HELM_EXTENSIONS_CACHE "/kaapana/mounted/extensions"
ENV HELM_PLATFORMS_CACHE "/kaapana/mounted/platforms"
ENV LOG_LEVEL="info"
ENV RECENT_UPDATE_CACHE="true"
ENV CONTAINERD_SOCK="/kaapana/mounted/containerd.sock"

EXPOSE 5000

CMD ["/bin/sh", "/kaapana/app/backend/boot.sh"]
