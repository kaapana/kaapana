FROM docker.io/alpine:3.19

LABEL IMAGE="subpath-reaper"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

# bash for the script, util-linux for nsenter+findmnt+umount, curl+jq to read the
# Kubernetes API, findutils/coreutils for portable find -mmin / date.
RUN apk add --no-cache bash util-linux curl jq findutils coreutils ca-certificates

COPY reap.sh /reap.sh
RUN chmod +x /reap.sh

ENTRYPOINT ["/reap.sh"]
