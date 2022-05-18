FROM python:3.9-alpine3.12
LABEL IMAGE="kube-helm"
LABEL VERSION="0.1.3"
LABEL CI_IGNORE="False"

RUN apk update && apk add --no-cache ca-certificates bash git openssh curl postgresql-dev python3-dev gcc musl-dev \ 
    && rm -rf /var/cache/apk/*

WORKDIR /app

ENV KUBE_LATEST_VERSION="v1.23.0"
ENV HELM_VERSION="v3.8.1"


RUN curl https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && curl https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz | tar -xzO linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm \
    && chmod g+rwx /root \
    && mkdir /config \
    && chmod g+rwx /config    
    
COPY files/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY files/backend/ ./

COPY files/update-collections-chart-0.1.0.tgz /root/collections/
COPY files/pull-docker-chart-0.1.1.tgz /root/helpers/
RUN chmod +x boot.sh

EXPOSE 5000

CMD ["./boot.sh"]
