# Builds the EUCAIM FEM-client from its public upstream source for the
# eucaim-fem-chart extension.
#
# The FEM-client source itself is public and needs no credentials to fetch
# (gitlab.bsc.es/fl/fem-client, plain `git clone`). What EUCAIM still keeps
# access-restricted per federation is the *config* repository
# ({project}-fem-client-config: config.py, json_launcher.json, TLS material,
# broker credentials) -- this chart supplies a Kaapana-specific equivalent of
# that config via ConfigMap/Secret (see ../eucaim-fem-chart), not via this
# image.
#
# Pinned to a specific commit for a reproducible build rather than tracking
# a branch. Building this image therefore needs network access to
# gitlab.bsc.es at image build time -- relevant for air-gapped Kaapana
# installs, which must pre-build/mirror this image instead.
FROM python:3.10-slim AS source

ARG FEM_CLIENT_GIT_URL=https://gitlab.bsc.es/fl/fem-client.git
# Commit this integration was developed and tested against.
ARG FEM_CLIENT_COMMIT=139d366112829eb4c79af03adbccb6bb1af95311

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    git clone "${FEM_CLIENT_GIT_URL}" /src && \
    cd /src && git checkout "${FEM_CLIENT_COMMIT}"

FROM python:3.10-slim

LABEL IMAGE="fem-client"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

# Deliberately NOT installing Docker / docker-compose and NOT mounting
# /var/run/docker.sock, unlike upstream's own Dockerfile. In this Kaapana
# integration, FEM-client's local "docker" executor is never invoked --
# json_launcher.json's submit_run command only curls fem-adapter, which
# drives workflow-api/Airflow to run the actual task as ordinary Kaapana
# pods. Giving a federated-task receiver access to the node's container
# runtime would let FEM-submitted tasks escape Kubernetes scheduling and
# Kaapana's per-project resource limits, so that access is never granted.
# One consequence: FEM-client's own health-check action shells out to
# `docker --version` / lists local docker images; both calls fail and are
# caught, surfacing as an "error" field in that action's response. That is
# an accepted, documented deviation from EUCAIM's reference (host + Docker)
# deployment model -- see the service README.
RUN apt-get update && \
    apt-get install -y --no-install-recommends bash curl ca-certificates gosu && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=source /src/app/ /app/
COPY --from=source /src/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# entrypoint.sh must start as root: it reconciles the container user/group
# to the UID/GID/DOCKER_GID env vars (groupadd/usermod/chown) before
# gosu-dropping to that user to run receiver.py. See eucaim-fem-chart's
# deployment template for the required env vars.
ENTRYPOINT ["/app/entrypoint.sh"]
