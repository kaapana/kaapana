FROM dorowu/ubuntu-desktop-lxde-vnc:focal

LABEL REGISTRY="local-only"
LABEL IMAGE="no-vnc-base"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

RUN sed -i 's#mirror://mirrors.ubuntu.com/mirrors.txt#http://archive.ubuntu.com/ubuntu/#' /etc/apt/sources.list;

RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -

<<<<<<< HEAD
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
    && rm -rf /var/lib/apt/lists/*

=======
COPY files/requirements.system /kaapana/app/
RUN apt-get update -y && cat /kaapana/app/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
>>>>>>> b0d47d1c823a51dd3af874a59ed61ecd4d468b94

COPY files/startup.sh /startup.sh

RUN chmod +x /startup.sh
