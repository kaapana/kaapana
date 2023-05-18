FROM local-only/base-podman:latest

LABEL IMAGE="build-kaapana"
LABEL VERSION="0.0.0"

LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
COPY files/docker_build.sh . 

ENTRYPOINT ["bash", "docker_build.sh"]
