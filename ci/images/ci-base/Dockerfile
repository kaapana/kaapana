# ci-base — the single CI job image
# Runs every job on the docker executors: deploy orchestration (ansible +
# kubernetes.core), integration tests (pytest/nmap/dcmsend), clean/notify,
# readthedocs checks — and the build jobs, whose docker CLI talks to the host
# daemon through the socket mount configured on the build runners (keeps the
# per-VM layer cache warm; `docker login` state dies with the job container).
# Build context is ci/ (repo root would ship the whole repo — no .dockerignore):
#   docker build -f ci/images/ci-base/Dockerfile -t <registry>/ci-base:<tag> ci
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        openssh-client \
        curl \
        ca-certificates \
        jq \
        nmap \
        dcmtk \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin \
    && rm -rf /var/lib/apt/lists/*

# helm + kubeval plugin: kaapana-build hard-fails without both
# (build_cli HelmChartHelper — chart lint + rendered-manifest validation).
ARG HELM_VERSION=3.19.0
RUN curl -fsSL "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" \
        | tar -xzO linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm \
    && helm plugin install https://github.com/instrumenta/helm-kubeval

# trivy: kaapana-build runs it as a plain process (build_cli TrivyHelper) —
# same pinned version the retired aquasec/trivy image had.
ARG TRIVY_VERSION=0.70.0
RUN curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
        | tar -xz -C /usr/local/bin trivy

# Same pinned dependency set as the runner-VM venvs (ci/harvester provisioning)
# so both worlds stay in sync during the migration.
COPY harvester/tasks/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Pre-bake the integration-test dependencies, then remove the package itself:
# jobs `pip install -e` the repo's current integration_tests at runtime (a
# no-op dependency-wise), so the image can never shadow MR changes to it.
COPY ci-code/integration_tests /tmp/integration_tests
RUN pip install --no-cache-dir /tmp/integration_tests \
    && pip uninstall -y integration-tests \
    && rm -rf /tmp/integration_tests
