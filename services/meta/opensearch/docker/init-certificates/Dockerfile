FROM docker.io/alpine:3.17.7

LABEL IMAGE="opensearch-certs"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

RUN apk add --no-cache openssl bash jq curl openjdk11
WORKDIR /certs

COPY files/generate-certificates.sh .
RUN chmod +x generate-certificates.sh
CMD [ "/bin/bash", "generate-certificates.sh" ]
