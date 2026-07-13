# Passthrough mirror of the upstream redis image into the Kaapana registry, following
# the same convention as busybox/kube-dashboard/minio. The Kaapana build pulls this at
# build time and pushes it as <registry_url>/redis:<kaapana_build_version>, so the
# oauth2-proxy redis session store also works on offline/air-gapped sites that can only
# reach the Kaapana registry.
FROM docker.io/redis:7.4-alpine

LABEL IMAGE="redis"
LABEL VERSION="7.4-alpine"
LABEL BUILD_IGNORE="False"
