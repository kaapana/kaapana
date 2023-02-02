FROM quay.io/keycloak/keycloak:19.0.3 as builder

WORKDIR /opt/keycloak
COPY files/kaapana /opt/keycloak/themes/kaapana
<<<<<<< HEAD
COPY files/login.jpg /opt/keycloak/themes/kaapana/login/resources/img/kaapana-bg.png
=======
COPY files/login.jpg /opt/keycloak/themes/kaapana/resources/img/kaapana-bg.png
>>>>>>> False path in Dockerfile.

RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:19.0.3

LABEL IMAGE="keycloak"
LABEL VERSION="19.0.3"
LABEL CI_IGNORE="False"

COPY --from=builder /opt/keycloak/ /opt/keycloak/
