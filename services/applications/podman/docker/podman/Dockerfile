FROM local-only/base-podman:latest

LABEL IMAGE="podman"
LABEL VERSION="4.4.1"

COPY files/kaapana.sh /kaapana/app/
RUN cat /kaapana/app/kaapana.sh >> ~/.bashrc