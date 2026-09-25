FROM ubuntu:24.04

LABEL REGISTRY="local-only"
LABEL IMAGE="base-code-server"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

# The one place code-server is installed. It is no longer part of base-python-cpu
# (0.7 GB in every processing image, used only when a development server is
# requested): code-server-init (services/applications/dev-server/docker) copies this
# install into a task pod's shared volumes at start-up, and the code-server
# applications copy it in at build time with a multi-stage FROM.

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install code server and python extension
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.127.0
RUN code-server --install-extension ms-python.python

# Fix bundled code-server node_module CVEs
# replace the following in all extension node_modules with patched versions
#   - undici      7.24.4 -> 7.28.0   (CVE-2026-12151, CVE-2026-6734, CVE-2026-9697)
#   - ws          8.19.0 -> 8.21.0   (CVE-2026-48779)
#   - shell-quote 1.8.3  -> 1.8.4    (CVE-2026-9277)
RUN for pkg_spec in \
        "undici:7.28.0" \
        "ws:8.21.0" \
        "shell-quote:1.8.4"; do \
        name="${pkg_spec%%:*}"; ver="${pkg_spec##*:}"; \
        wget -q "https://registry.npmjs.org/${name}/-/${name}-${ver}.tgz" -O /tmp/npmpkg.tgz && \
        rm -rf /tmp/package && tar -xzf /tmp/npmpkg.tgz -C /tmp && \
        for dir in $(find /usr/lib/code-server /root/.local/share/code-server -path "*/node_modules/${name}" -type d 2>/dev/null); do \
            cp -rf /tmp/package/. "$dir/"; \
        done; \
        rm -rf /tmp/package /tmp/npmpkg.tgz; \
    done
