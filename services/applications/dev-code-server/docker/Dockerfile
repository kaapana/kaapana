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
    && rm -rf /var/lib/apt/lists/*

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

# Install code-server extensions for notebooks/R plus Continue AI assistant.
# Pin the Continue version to avoid breaking changes in the inline-completion
# provider when a new release lands on Open VSX.
RUN code-server --install-extension ms-toolsai.jupyter && \
    code-server --install-extension REditorSupport.r && \
    code-server --install-extension ms-toolsai.jupyter-keymap && \
    code-server --install-extension ms-toolsai.jupyter-renderers && \
    code-server --install-extension Continue.continue@1.2.16

# Create workspace & entrypoint
WORKDIR /kaapana
EXPOSE 8080

COPY files/entrypoint.sh /entrypoint.sh
COPY files/README.md /kaapana/README.md
# Continue extension reads global config from `~/.continue/config.yaml`.
COPY files/continue-config.yaml /etc/kaapana/continue-config.yaml

RUN mkdir -p /root/.continue && \
    cp /etc/kaapana/continue-config.yaml /root/.continue/config.yaml && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
