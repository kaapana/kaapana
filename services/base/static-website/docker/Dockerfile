FROM nginxinc/nginx-unprivileged:1.25.4-alpine

COPY files/ /kaapana/app/

LABEL IMAGE="static-website"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

USER 1000
