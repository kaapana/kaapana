FROM jboss/keycloak:16.1.1


LABEL IMAGE="keycloak"
LABEL VERSION="16.1.1"
LABEL CI_IGNORE="False"


COPY files/messages_en.properties /opt/jboss/keycloak/themes/base/login/messages/messages_en.properties
COPY files/login.jpg /opt/jboss/keycloak/themes/keycloak/login/resources/img/keycloak-bg.png
# COPY files/login.css /opt/jboss/keycloak/themes/keycloak/login/resources/css/login.css
