FROM ubuntu:24.04

LABEL IMAGE="dev-code-server"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Install basic dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    ca-certificates \
    apt-transport-https \
    gnupg \
    lsb-release \
    locales \
    python3 \
    python3-pip \
    python3-venv \
    git \
    unzip \
    libssl-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    software-properties-common \
    gdebi-core \
    sudo \
    && locale-gen en_US.UTF-8 \
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

# Python environment setup
RUN apt-get update && apt-get install -y --no-install-recommends python3-full && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir jupyterlab ipykernel jupyter matplotlib pandas numpy scipy && \
    /opt/venv/bin/pip --no-cache-dir install torch torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118 && \
    echo "source /opt/venv/bin/activate" >> /etc/bash.bashrc
ENV PATH="/opt/venv/bin:$PATH"

# Install Code Server manually
RUN wget -q https://code-server.dev/install.sh -O /tmp/install.sh && \
    bash /tmp/install.sh --version 4.105.1 && \
    rm /tmp/install.sh

# Install VS Code extensions
RUN code-server --install-extension ms-python.python && \
    code-server --install-extension ms-toolsai.jupyter && \
    code-server --install-extension REditorSupport.r && \
    code-server --install-extension ms-toolsai.jupyter-keymap && \
    code-server --install-extension ms-toolsai.jupyter-renderers

# Enable GPU - currently disabled but can be reenabled if a GPU from multiple GPUs can be assigned properly in an init job

# ARG CUDA_VERSION
# LABEL com.nvidia.volumes.needed="nvidia_driver"
# ENV NVIDIA_VISIBLE_DEVICES all
# ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
# ENV LD_LIBRARY_PATH /usr/local/nvidia/lib:/usr/local/nvidia/lib64

# RUN apt-get update -y && apt-get install -y --no-install-recommends \
#     libgl1 \
#     && rm -rf /var/lib/apt/lists/*

# Create workspace & entrypoint
WORKDIR /workspace
EXPOSE 8080

COPY files/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
