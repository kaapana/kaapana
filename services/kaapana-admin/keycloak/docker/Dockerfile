FROM local-only/base-python-cpu:latest as builder

WORKDIR /app
RUN git clone  --single-branch --depth 1 --branch 21.0.1 https://github.com/keycloak/keycloak.git /app/keycloak-repo
RUN cp -r /app/keycloak-repo/themes/src/main/resources/theme/keycloak/ /app/kaapana
COPY files/login.css /app/kaapana/login/resources/css/login.css
COPY files/login.jpg /app/kaapana/login/resources/img/kaapana-bg.png

################################################################## NEW STAGE ########################################################################
FROM quay.io/keycloak/keycloak:21.0.1
LABEL IMAGE="keycloak"
LABEL VERSION="21.0.1"
LABEL CI_IGNORE="False"

COPY --from=builder /app/kaapana /opt/keycloak/themes/kaapana
