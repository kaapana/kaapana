FROM jboss/keycloak:11.0.2


LABEL IMAGE="keycloak"
LABEL VERSION="11.0.2-vdev"
LABEL CI_IGNORE="False"


COPY files/messages_en.properties /opt/jboss/keycloak/themes/base/login/messages/messages_en.properties
COPY files/login.jpg /opt/jboss/keycloak/themes/keycloak/login/resources/img/keycloak-bg.png
# COPY files/login.css /opt/jboss/keycloak/themes/keycloak/login/resources/css/login.css
