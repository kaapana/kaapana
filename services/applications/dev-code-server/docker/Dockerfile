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

# Install R. The R packages build from source: fs (needed by languageserver) links
# libuv, systemfonts (needed by httpgd) fontconfig and freetype. install.packages
# only warns when a package fails, so the check after it fails the build instead.
RUN mkdir -p /usr/share/keyrings && \
    curl -fsSL https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc \
        | gpg --dearmor -o /usr/share/keyrings/cran.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cran.gpg] https://cloud.r-project.org/bin/linux/ubuntu noble-cran40/" \
        > /etc/apt/sources.list.d/cran.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends r-base r-base-dev \
        libuv1-dev libfontconfig1-dev libfreetype-dev && \
    rm -rf /var/lib/apt/lists/* && \
    R --silent --no-echo --no-save --no-restore -e "pkgs <- c('languageserver','httpgd'); install.packages(pkgs, repos='https://cloud.r-project.org'); stopifnot(all(sapply(pkgs, requireNamespace, quietly = TRUE)))"

# Install code-server extensions
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
