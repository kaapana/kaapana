FROM local-only/base-desktop:latest

LABEL IMAGE="slicer-workbench"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpulse-dev \
    libglu1-mesa \
    libnss3 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    xauth \
    && rm -rf /var/lib/apt/lists/*

# Slicer 5.8.1
RUN set -eux; \
    SLICER_URL="https://download.slicer.org/bitstream/67c51fc129825655577cfee9"; \
    curl -k -v -sS -L -f --retry 5 --retry-delay 5 --retry-connrefused \
      -o /tmp/slicer.tar.gz "$SLICER_URL"; \
    tar -xzf /tmp/slicer.tar.gz -C /tmp; \
    mv /tmp/Slicer* /opt/slicer; \
    rm -f /tmp/slicer.tar.gz

RUN chmod -R a+w /opt/slicer

# install Slicer extension; extension name hardcoded in install-slicer-extension.py
COPY files/install-slicer-extension.py /opt/slicer

# Slicer specific adjustements, using the default user in $USER
RUN rm /home/$USER/.bashrc /home/$USER/.bash_logout /home/$USER/.profile \
    && sed -i -e '/^PS1/s/^/#/' /etc/bash.bashrc \
    && sed -i -e '/stdout.*uname/s/^/#/' /etc/pam.d/login \
    && echo 'source /etc/profile.d/prompt.sh' >> /etc/bash.bashrc \
    && echo "allowed_users=anybody" > /etc/X11/Xwrapper.config \
    && su $USER -c "mkdir -p /home/$USER/Documents" \
    && su $USER -c "xvfb-run --auto-servernum \
        /opt/slicer/Slicer --python-script /opt/slicer/install-slicer-extension.py --no-splash --no-main-window"

RUN ln -s /kaapana/minio /home/$USER/Desktop/data
WORKDIR /kaapana/minio

COPY files/supervisor-slicer.conf /etc/supervisor/conf.d/