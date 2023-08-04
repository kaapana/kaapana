FROM docker.io/alpine:3.17.2

LABEL IMAGE="cert-init"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

ENV KUBE_LATEST_VERSION="v1.26.1"
# RUN apk add --no-cache kubectl --repository=http://dl-cdn.alpinelinux.org/alpine/edge/testing/x86_64
RUN apk add --no-cache openssl bash jq curl
RUN curl https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl

WORKDIR /cert
COPY handle-secret.sh .
CMD ["./handle-secret.sh"]
