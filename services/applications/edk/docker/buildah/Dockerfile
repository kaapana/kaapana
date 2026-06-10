FROM debian:bookworm-slim

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    buildah \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 1000 --create-home --shell /bin/sh user

LABEL IMAGE="buildah"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

COPY --chown=1000:1000 files/start.sh /start.sh
RUN chmod +x /start.sh
