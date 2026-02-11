FROM local-only/base-python-gpu:latest

LABEL IMAGE="dev-code-server"
LABEL BUILD_IGNORE="False"

RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    libssl-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    software-properties-common \
    gdebi-core \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl for GPU job management
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0700 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# Install R
RUN mkdir -p /usr/share/keyrings && \
    curl -fsSL https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc \
        | gpg --dearmor -o /usr/share/keyrings/cran.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cran.gpg] https://cloud.r-project.org/bin/linux/ubuntu noble-cran40/" \
        > /etc/apt/sources.list.d/cran.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends r-base r-base-dev && \
    rm -rf /var/lib/apt/lists/* && \
    R --silent --no-echo --no-save --no-restore -e "install.packages(c('languageserver','httpgd'), repos='https://cloud.r-project.org')"

# Create workspace & entrypoint
WORKDIR /kaapana
EXPOSE 8080

COPY files/entrypoint.sh /entrypoint.sh
COPY files/gpu-run /usr/local/bin/gpu-run
COPY files/gpu-run-root /usr/local/bin/gpu-run-root

# Set permissions: gpu-run executable by all, editable only by root
RUN chmod 755 /entrypoint.sh /usr/local/bin/gpu-run

COPY files/README.md /kaapana/README.md

# Add non-root user 'coder' and set as default
RUN useradd -m -s /bin/bash coder

# Make the shared venv writable by coder so they can pip-install packages
RUN chown -R coder:coder /opt/venv

# Configure coder's shell: activate venv and set git identity
RUN echo 'source /opt/venv/bin/activate' >> /home/coder/.bashrc && \
    git config --system user.name "coder" && \
    git config --system user.email "coder@kaapana.local"

# Add sudoers entry (recommended: /etc/sudoers.d/*)
RUN set -eux; \
    printf '%s\n' \
      'Cmnd_Alias MYCMD = /usr/local/bin/gpu-run-root' \
      'coder ALL=(root) NOPASSWD: MYCMD' \
      'Defaults!MYCMD env_keep += "GPU_JOB_NAMESPACE RELEASE_NAME KUBERNETES_SERVICE_HOST KUBERNETES_SERVICE_PORT http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY"' \
    > /etc/sudoers.d/myuser-mycmd; \
    chmod 0440 /etc/sudoers.d/myuser-mycmd; \
    visudo -cf /etc/sudoers.d/myuser-mycmd; \
    visudo -cf /etc/sudoers

RUN chown -R coder:coder /kaapana
RUN chmod 755 /kaapana

USER coder

# Install code-server extensions as coder user so they land in ~coder
RUN code-server --install-extension ms-toolsai.jupyter && \
    code-server --install-extension REditorSupport.r && \
    code-server --install-extension ms-toolsai.jupyter-keymap && \
    code-server --install-extension ms-toolsai.jupyter-renderers && \
    code-server --install-extension ms-python.python

ENTRYPOINT ["/entrypoint.sh"]
