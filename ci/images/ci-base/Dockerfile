# ci-base — the single CI job image: ansible, helm, trivy, docker CLI, dcmtk,
# nmap, node/npm, chromium, and the pinned Python test deps.
# Build context is ci/ (not the repo root — no .dockerignore exists):
#   docker build -f ci/images/ci-base/Dockerfile -t <registry>/ci-base:<tag> ci
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        git-lfs \
        openssh-client \
        curl \
        ca-certificates \
        jq \
        nmap \
        dcmtk \
        nodejs \
        npm \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install --system

# helm + kubeval plugin: kaapana-build hard-fails without both
ARG HELM_VERSION=3.19.0
RUN curl -fsSL "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" \
        | tar -xzO linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm \
    && helm plugin install https://github.com/instrumenta/helm-kubeval

# trivy: kaapana-build runs it as a plain process
ARG TRIVY_VERSION=0.70.0
RUN curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
        | tar -xz -C /usr/local/bin trivy

# Pinned ansible/tooling deps (shared with ci/harvester provisioning)
COPY harvester/tasks/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Pre-bake the integration-test deps, then remove the package itself: jobs
# `pip install -e` the repo's current code, so the image never shadows MR changes.
COPY ci-code/integration_tests /tmp/integration_tests
RUN pip install --no-cache-dir /tmp/integration_tests \
    && pip uninstall -y integration-tests \
    && rm -rf /tmp/integration_tests

# Chromium + its system libraries for the playwright-based integration tests
RUN python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*
