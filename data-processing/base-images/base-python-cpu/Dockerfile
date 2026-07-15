FROM ubuntu:24.04

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-cpu"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive

# Remove default non-root user 1000 introduced in ubuntu23.04, it affects all adduser commands in subsequent Dockerfiles
# https://bugs.launchpad.net/cloud-images/+bug/2005129
RUN userdel -r ubuntu

# Install apt packages
WORKDIR /app
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    git \
    htop \
    zip \
    unzip \
    nano \
    dcmtk \
    ca-certificates \
    build-essential \
    wget \
    curl \
    procps \
    python3.12 \
    python3.12-venv \
    python3-pip \
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

# For python3.11+ externally managed environments are introduced
# It requires the use of venv, see PEP668 https://peps.python.org/pep-0668/

# Create venv to handle pip installations
RUN python3 -m venv /opt/venv
# Activate venv and upgrade pip inside it
RUN /opt/venv/bin/pip install --upgrade pip
# Make venv's python and pip accessible in the PATH
ENV PATH="/opt/venv/bin:$PATH"

# Install torch for cuda 11.8
RUN pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu118

# Install requirements
COPY files/requirements.txt /app/
RUN python3 -m pip install --upgrade setuptools pip && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt -r /app/requirements.txt

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

# Copy and install kaapana_federated directly from source
COPY files/kaapana_federated /app/kaapana_federated
RUN python3 -m pip install /app/kaapana_federated

# Install kaapanapy pip package
COPY files/kaapanapy-shim /app/kaapanapy-shim
WORKDIR /app/kaapanapy-shim
RUN python3 -m build 
RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt dist/kaapanapy-0.0.1.tar.gz

WORKDIR /kaapana/app
