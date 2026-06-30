# Mirror of the upstream nnInteractive inference server image. At build time this
# pulls the external image, re-tags it under the platform registry, and pushes it
# there, so at deploy time it is served from the same registry as every other
# Kaapana image instead of being pulled directly from ghcr.io.
FROM ghcr.io/mic-dkfz/nninteractive-server:2.5.0-nninteractive_v1.0

LABEL IMAGE="nninteractive-server"
LABEL VERSION="2.5.0-nninteractive_v1.0"
LABEL BUILD_IGNORE="False"
