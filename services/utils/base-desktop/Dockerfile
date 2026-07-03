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
        jgmenu \
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
        tint2 \
        ttf-wqy-zenhei \
        vim-tiny \
        webp-pixbuf-loader \
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
COPY files/logo.png /opt/novnc/logo.png
COPY files/favicon.png /opt/novnc/favicon.png
RUN git clone --depth 1 --branch v0.12.0 https://github.com/novnc/websockify /opt/novnc/utils/websockify
COPY /files/etc /etc
COPY /files/root /root
COPY /files/usr /usr

# kaapana menu launcher icon (brain mark, reused from the noVNC loading logo)
COPY files/logo.png /usr/share/kaapana/kaapana.png

# single desktop (removes the workspace pager view) + dark openbox window decorations
RUN sed -i \
        -e 's|<number>4</number>|<number>1</number>|' \
        -e 's|<name>Clearlooks</name>|<name>Onyx</name>|' \
        /etc/xdg/openbox/rc.xml

# register the webp gdk-pixbuf loader so pcmanfm can render the .webp wallpaper
RUN /usr/lib/x86_64-linux-gnu/gdk-pixbuf-2.0/gdk-pixbuf-query-loaders --update-cache

RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt -r /usr/local/lib/backend/requirements.txt

EXPOSE 80
WORKDIR /root
ENV HOME=/root \
    SHELL=/bin/bash

# Default User
ENV USER=researcher
RUN useradd -m $USER -s /bin/bash -u 1000 -G sudo \
    && echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$USER \
    && su $USER -c "mkdir -p /home/researcher/Desktop"

# Note: if sudo access should not be possible in derived containers:
# RUN  rm /etc/sudoers.d/$USER

COPY files/startup.sh /startup.sh
ENTRYPOINT ["/startup.sh"]