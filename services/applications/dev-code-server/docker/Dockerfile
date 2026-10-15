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

# Install code-server extensions
RUN code-server --install-extension ms-toolsai.jupyter && \
    code-server --install-extension REditorSupport.r && \
    code-server --install-extension ms-toolsai.jupyter-keymap && \
    code-server --install-extension ms-toolsai.jupyter-renderers

# Continue AI assistant, pinned because the patch below edits its bundled code.
# Its autocomplete reads the clipboard for context, which never returns in
# code-server's browser setup, so every completion would hang until cancelled.
# The grep fails the build when a new Continue version no longer matches.
RUN code-server --install-extension Continue.continue@1.2.16 && \
    ext=$(ls /root/.local/share/code-server/extensions/continue.continue-*/out/extension.js) && \
    sed -i 's/getClipboardSnippets = async (ide) => {/getClipboardSnippets = async (ide) => { return [];/' "$ext" && \
    grep -q 'getClipboardSnippets = async (ide) => { return \[\];' "$ext"

# Create workspace & entrypoint
WORKDIR /kaapana
EXPOSE 8080

COPY files/entrypoint.sh /entrypoint.sh
COPY files/README.md /kaapana/README.md

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
