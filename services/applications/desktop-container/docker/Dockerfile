FROM local-only/base-desktop:latest

LABEL IMAGE="desktop-container"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

RUN ln -s /kaapana/minio /home/$USER/Desktop/data
WORKDIR /kaapana/minio

# As an kaapana admin, you can build and install software here, that should be part of
# the desktop-container.

