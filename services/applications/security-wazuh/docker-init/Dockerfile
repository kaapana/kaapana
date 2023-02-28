FROM wazuh/wazuh-certs-generator:0.0.1 as build-stage

# the provided script from wazuh does not work if curl is called behind a proxy -> make it more robust
RUN sed -i 's/curl --silent -I $PACKAGES_URL$CERT_TOOL | grep -E "^HTTP" | awk  \x27{print $2}\x27/curl --silent -o \/dev\/null -I -w "%{http_code}" \$PACKAGES_URL\$CERT_TOOL/' /entrypoint.sh
RUN sed -i 's/curl --silent -I $PACKAGES_DEV_URL$CERT_TOOL | grep -E "^HTTP" | awk  \x27{print $2}\x27/curl --silent -o \/dev\/null -I -w "%{http_code}" \$PACKAGES_DEV_URL\$CERT_TOOL/' /entrypoint.sh

RUN apt-get update && apt-get upgrade -y && apt-get install -y git curl \
    && rm -rf /var/cache/apk/*

RUN git clone https://github.com/wazuh/wazuh-docker.git -b v4.3.9 --depth=1 -c advice.detachedHead=false

RUN mkdir /config && mv /wazuh-docker/single-node/config/* /config && rm -rf /wazuh-docker

RUN mkdir /certificates
RUN /entrypoint.sh

FROM alpine:3.16.2

LABEL IMAGE="security-wazuh-init"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

RUN apk update && apk add --no-cache sed

COPY files/ ./
RUN chmod +x init.sh

RUN mkdir /tmp-config && mkdir /tmp-certificates
COPY --from=build-stage /config/ /tmp-config/
COPY --from=build-stage /certificates/ /tmp-certificates/

WORKDIR /wazuh-config

ENTRYPOINT ["/init.sh"]