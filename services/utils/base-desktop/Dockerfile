FROM local-only/base-python-gpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-desktop"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        alsa-utils \
        apache2-utils \
        arc-theme \
        at-spi2-core \
        ca-certificates \
        curl \
        dbus-x11 \
        ffmpeg \
        gedit \
        gnome-themes-extra \
        # gnome-themes-standard \
        gnupg \
        gpg-agent \
        gpgconf \
        gtk2-engines-murrine \
        gtk2-engines-pixbuf \
        libgl1-mesa-dri \
        libglu1-mesa-dev \
        libgomp1 \
        libqt5opengl5-dev \
        libqt5svg5-dev \
        libqt5webengine-data \
        libqt5x11extras5-dev \
        libqt5xmlpatterns5-dev \
        libssl-dev \
        libtiff5-dev \
        libwrap0-dev \
        libxcb-cursor0 \
        libxcomposite1 \
        libxcursor1 \
        libxi-dev \
        libxkbcommon-x11-0 \
        libxt-dev \
        lightdm \
        linux-libc-dev \
        lxde \
        mesa-common-dev \
        mesa-utils \
        net-tools \
        python3-pip \
        qtbase5-dev \
        qtscript5-dev \
        qttools5-dev \
        qtwebengine5-dev \
        qtxmlpatterns5-dev-tools \
        software-properties-common \
        sudo \
        supervisor \
        ttf-wqy-zenhei \
        vim-tiny \
        wmctrl \
        x11-utils \
        x11vnc \
        xvfb \
        xz-utils \
        zenity \
        nginx \
        xcvt \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && (dpkg -i ./google-chrome-stable_current_amd64.deb || apt-get install -fy) \
    && curl -sSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add \
    && rm google-chrome-stable_current_amd64.deb

# tini to fix subreap
ARG TINI_VERSION=v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /bin/tini
RUN chmod +x /bin/tini

ARG NOVNC_VERSION=v1.5.0
RUN git clone --depth 1 --branch ${NOVNC_VERSION} https://github.com/novnc/noVNC.git /opt/novnc
COPY files/index.html /opt/novnc/index.html
RUN git clone --depth 1 --branch v0.12.0 https://github.com/novnc/websockify /opt/novnc/utils/websockify
COPY /files/etc /etc
COPY /files/root /root
COPY /files/usr /usr

RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /usr/local/lib/backend/requirements.txt

EXPOSE 80
WORKDIR /root
ENV HOME=/root \
    SHELL=/bin/bash

# Default User
ENV USER=researcher
RUN useradd -m researcher -s /bin/bash -u 1000 \
    && gpasswd -a researcher sudo \
    && passwd -d researcher && passwd -u researcher \
    && su researcher -c "mkdir -p /home/researcher/Desktop"

COPY files/startup.sh /startup.sh
ENTRYPOINT ["/startup.sh"]