FROM python:3.10.6-alpine3.16
LABEL IMAGE="kube-helm"
LABEL VERSION="0.1.4"
LABEL CI_IGNORE="False"

RUN apk update && apk add --no-cache ca-certificates bash git openssh curl postgresql-dev python3-dev gcc musl-dev \ 
    && rm -rf /var/cache/apk/*

WORKDIR /app

ENV KUBE_LATEST_VERSION="v1.23.0"
ENV HELM_VERSION="v3.8.1"

RUN curl https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl
RUN curl https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz | tar -xzO linux-amd64/helm > /usr/local/bin/helm && chmod +x /usr/local/bin/helm
RUN chmod g+rwx /root && mkdir /config && chmod g+rwx /config    

COPY files/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY files/backend /app/backend

COPY files/update-collections-chart /root/collections/update-collections-chart
RUN /usr/local/bin/helm package /root/collections/update-collections-chart -d /root/collections
COPY files/pull-docker-chart /root/helpers/pull-docker-chart
RUN /usr/local/bin/helm package /root/helpers/pull-docker-chart -d /root/helpers

ENV HELM_PATH "/usr/local/bin/helm"
ENV KUBECTL_PATH "kubectl"
ENV HELM_EXTENSIONS_CACHE "/root/extensions"
ENV LOG_LEVEL="debug"
ENV RECENT_UPDATE_CACHE="true"

EXPOSE 5000
CMD ["gunicorn","main:app","--chdir","/app/backend/app","--workers","1","--worker-class","uvicorn.workers.UvicornWorker","--bind","0.0.0.0:5000","--access-logfile","-","--error-logfile","-"]
