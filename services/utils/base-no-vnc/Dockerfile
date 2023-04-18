################################################################################
# builder
################################################################################

FROM local-only/base-python-cpu:latest as builder


RUN sed -i 's#http://archive.ubuntu.com/ubuntu/#mirror://mirrors.ubuntu.com/mirrors.txt#' /etc/apt/sources.list;


RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg patch

# nodejs
RUN curl -sL https://deb.nodesource.com/setup_16.x | bash - \
    && apt-get install -y nodejs

# yarn
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y yarn

# build frontend
RUN apt-get install -y git
RUN git clone https://github.com/Tiryoh/docker-ubuntu-vnc-desktop.git /docker-ubuntu-desktop 
RUN cd /docker-ubuntu-desktop \
    && git checkout ce74b4184465c2ff6299052476296d6c6947b200 \
    && git submodule init \
    && git submodule update
RUN mkdir /src  && cp -r /docker-ubuntu-desktop/web /src
RUN cd /src/web \
    && yarn config set network-timeout 600000 \
    && yarn \
    && yarn build
RUN sed -i 's#app/locale/#novnc/app/locale/#' /src/web/dist/static/novnc/app/ui.js


FROM local-only/base-python-cpu:latest as system


# based on https://github.com/fcwu/docker-ubuntu-vnc-desktop
# and https://github.com/Tiryoh/docker-ubuntu-vnc-desktop
################################################################################
# base system
################################################################################

LABEL REGISTRY="local-only"
LABEL IMAGE="no-vnc-base"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i 's#http://archive.ubuntu.com/ubuntu/#mirror://mirrors.ubuntu.com/mirrors.txt#' /etc/apt/sources.list;

# built-in packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends software-properties-common curl apache2-utils \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        supervisor nginx sudo net-tools zenity xz-utils \
        dbus-x11 x11-utils alsa-utils \
        mesa-utils libgl1-mesa-dri \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
# install debs error if combine together
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xvfb x11vnc \
        vim-tiny \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gpgconf gnupg gpg-agent \
    && curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && (dpkg -i ./google-chrome-stable_current_amd64.deb || apt-get install -fy) \
    && curl -sSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        lightdm \
    && apt-get install -y \
        lxde \
    && apt-get install -y --no-install-recommends \
        gtk2-engines-murrine gnome-themes-standard gtk2-engines-pixbuf gtk2-engines-murrine arc-theme \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
# Additional packages require ~600MB
# libreoffice  pinta language-pack-zh-hant language-pack-gnome-zh-hant firefox-locale-zh-hant libreoffice-l10n-zh-tw

# tini to fix subreap
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ffmpeg
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /usr/local/ffmpeg \
    && ln -s /usr/bin/ffmpeg /usr/local/ffmpeg/ffmpeg

# python library
RUN curl https://raw.githubusercontent.com/Tiryoh/docker-ubuntu-vnc-desktop/3ca98db34cebd7cbd907b6cae9731a049ec2eec1/rootfs/usr/local/lib/web/backend/requirements.txt > /tmp/requirements.txt
RUN apt-get update \
    && dpkg-query -W -f='${Package}\n' > /tmp/a.txt \
    && apt-get install -y python3-pip python3-dev build-essential \
	&& python3 -m pip install setuptools wheel && python3 -m pip install -r /tmp/requirements.txt \
    && dpkg-query -W -f='${Package}\n' > /tmp/b.txt \
    && apt-get remove -y `diff --changed-group-format='%>' --unchanged-group-format='' /tmp/a.txt /tmp/b.txt | xargs` \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* /tmp/a.txt /tmp/b.txt

# terminator
RUN apt-get update \
    && apt-get install -yq --no-install-recommends terminator \
    && sudo apt-get purge -y tilix \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*





################################################################################
# merge
################################################################################
#FROM system


COPY --from=builder /src/web/dist/ /usr/local/lib/web/frontend/
COPY --from=builder /docker-ubuntu-desktop/rootfs /
RUN ln -sf /usr/local/lib/web/frontend/static/websockify /usr/local/lib/web/frontend/static/novnc/utils/websockify && \
	chmod +x /usr/local/lib/web/frontend/static/websockify/run

EXPOSE 80
WORKDIR /root
ENV HOME=/home/ubuntu \
    SHELL=/bin/bash
HEALTHCHECK --interval=30s --timeout=5s CMD curl --fail http://127.0.0.1:6079/api/health
ENTRYPOINT ["/startup.sh"]

################################################################################
# kaapana sepcifics
################################################################################
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    libtiff5-dev \
    libwrap0-dev \
    libxcomposite1 \
    libxcursor1 \
    libxi-dev \
    libxkbcommon-x11-0 \
    mesa-common-dev \
    libssl-dev \
    wmctrl \
    libglu1-mesa-dev \
    libxt-dev \
    libgomp1 \
    xvfb \
    qtbase5-dev \
    qtscript5-dev \
    libqt5svg5-dev \
    libqt5opengl5-dev \
    libqt5xmlpatterns5-dev \
    qtwebengine5-dev \
    qttools5-dev \
    libqt5x11extras5-dev \
    qtxmlpatterns5-dev-tools \
    libqt5webengine-data \
    at-spi2-core \
    gedit \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*
    

RUN pip install --no-cache-dir \
    # Security fix for CVE-2021-33503
    urllib3==1.26.5 \
    # Security fix for CVE-2022-40898
    wheel==0.38.1 \
    # Security fix for CVE-2023-25577
    Werkzeug==2.2.3 \
    # Werkzeug 2.0.0+ breaks Flask
    Flask==2.2.3 \
    Jinja2==3.1.2

COPY files/startup.sh /startup.sh

RUN chmod +x /startup.sh
