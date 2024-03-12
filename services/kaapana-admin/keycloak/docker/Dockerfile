FROM local-only/base-python-cpu:latest as builder

WORKDIR /app
RUN git clone  --single-branch --depth 1 --branch 23.0.4 https://github.com/keycloak/keycloak.git /app/keycloak-repo
RUN cp -r /app/keycloak-repo/themes/src/main/resources/theme/keycloak/ /app/kaapana
COPY files/login.css /app/kaapana/login/resources/css/login.css
COPY files/login.jpg /app/kaapana/login/resources/img/kaapana-bg.png

## Fix for update to 23.0.4 -> https://github.com/keycloak/keycloak/issues/12719#issuecomment-1858575991
RUN sed -i '/^stylesCommon=/c\stylesCommon=node_modules/@patternfly/patternfly/patternfly.min.css node_modules/patternfly/dist/css/patternfly.min.css node_modules/patternfly/dist/css/patternfly-additions.min.css lib/pficon/pficon.css' /app/kaapana/login/theme.properties

################################################################# NEW STAGE ########################################################################
FROM quay.io/keycloak/keycloak:23.0.4
LABEL IMAGE="keycloak"
LABEL VERSION="23.0.4"
LABEL BUILD_IGNORE="False"

COPY --from=builder /app/kaapana /opt/keycloak/themes/kaapana
