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

# Install R from CRAN
RUN mkdir -p /usr/share/keyrings && \
    gpg --batch --keyserver keyserver.ubuntu.com --recv-keys 51716619E084DAB9 && \
    gpg --export 51716619E084DAB9 | gpg --dearmor > /usr/share/keyrings/cran-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cran-archive-keyring.gpg] https://cloud.r-project.org/bin/linux/ubuntu noble-cran40/" \
        > /etc/apt/sources.list.d/cran.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends r-base r-base-dev && \
    rm -rf /var/lib/apt/lists/* && \
    /usr/bin/R --silent --no-echo --no-save --no-restore -e "install.packages('languageserver', repos='https://cloud.r-project.org/')"

RUN code-server --install-extension ms-toolsai.jupyter && \
    code-server --install-extension REditorSupport.r && \
    code-server --install-extension ms-toolsai.jupyter-keymap && \
    code-server --install-extension ms-toolsai.jupyter-renderers

# Create workspace & entrypoint
WORKDIR /kaapana
EXPOSE 8080

COPY files/entrypoint.sh /entrypoint.sh
COPY files/README.md /kaapana/README.md

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
