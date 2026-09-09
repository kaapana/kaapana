FROM local-only/base-installer:latest

LABEL IMAGE="kaapana-extension-collection"
LABEL BUILD_IGNORE="False"

COPY --from=charts charts/*.tgz /kaapana/tmp/extensions/
