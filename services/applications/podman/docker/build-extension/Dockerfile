FROM local-only/base-podman:latest

LABEL IMAGE="build-kaapana-extension"
LABEL VERSION="0.0.0"

LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
COPY files/* . 

# ENV GIT_REPOSITORY="https://github.com/kaapana/kaapana.git"
# ENV BRANCH="develop"
# ENV KAAPANA_VERSION="0.0.0-latest"

# RUN ./kaapana_build.sh -gr https://github.com/kaapana/kaapana.git -b develop

# ENTRYPOINT [ "bash", "extension_build.sh"]
