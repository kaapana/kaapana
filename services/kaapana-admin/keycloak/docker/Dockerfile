FROM local-only/base-python-cpu:latest as downloader

WORKDIR /

RUN git clone  --single-branch --depth 1 --branch 19.0.3 https://github.com/keycloak/keycloak.git keycloak-repo && cd keycloak-repo && git checkout 1641fbb
RUN cp -r keycloak-repo/themes/src/main/resources/theme/keycloak/ keycloak

FROM quay.io/keycloak/keycloak:19.0.3 as builder

WORKDIR /opt/keycloak

COPY --from=downloader /keycloak/ /opt/keycloak/themes/kaapana
COPY files/login.css /opt/keycloak/themes/kaapana/login/resources/css/login.css
COPY files/login.jpg /opt/keycloak/themes/kaapana/login/resources/img/kaapana-bg.png

RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:19.0.3

LABEL IMAGE="keycloak"
LABEL VERSION="19.0.3"
LABEL CI_IGNORE="False"

COPY --from=builder /opt/keycloak/ /opt/keycloak/