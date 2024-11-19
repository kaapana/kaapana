FROM local-only/no-vnc-base:latest

LABEL IMAGE="desktop-container"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="True"

RUN mkdir  -p /home/desktop/Desktop/
RUN ln -s /kaapana/minio /home/desktop/Desktop/
WORKDIR /kaapana/minio



RUN useradd -u 1000 -ms /bin/bash desktop
RUN chown -R desktop /home/desktop



# As an kaapana admin, you can build and install software here, that should be part of 
# the desktop-container.

