FROM medicalinformatics/mainzelliste:1.10.5

LABEL IMAGE="mainzelliste"
LABEL VERSION="1.10.5"
LABEL CI_IGNORE="False"

COPY --chown=ml:www-data /files/mainzelliste.conf $CATALINA_HOME/webapps/ROOT/WEB-INF/classes/mainzelliste.docker.conf
#COPY --chown=ml:www-data /files/mainzelliste.conf /run/secrets/mainzellisteConf