FROM local-only/base-kaapana:latest

LABEL IMAGE="kaapana"
LABEL VERSION="0.0.0"

LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
COPY files/docker_build.sh . 

ENTRYPOINT ["bash", "docker_build.sh"]
