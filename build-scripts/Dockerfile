FROM local-only/base-kaapana:latest

LABEL IMAGE="kaapana"
LABEL VERSION="0.0.0"

WORKDIR /kaapana/app
COPY docker_build.sh . 

ENTRYPOINT ["bash", "docker_build.sh"]
