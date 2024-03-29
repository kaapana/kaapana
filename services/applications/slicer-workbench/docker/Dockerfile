FROM local-only/no-vnc-base:latest

LABEL IMAGE="slicer-workbench"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /src
RUN mkdir -p /kaapana/mounted/slicer-data

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
    xvfb \
    xauth \
    && rm -rf /var/lib/apt/lists/*

# Slicer 5.6.1
RUN SLICER_URL="https://download.slicer.org/bitstream/657813b183a3201b44d4e6f7" && \
    curl -k -v -s -L $SLICER_URL | tar xz -C /tmp && \
    mv /tmp/Slicer* /opt/slicer

RUN chmod -R a+w /opt/slicer

RUN useradd -m researcher -s /bin/bash && \
    gpasswd -a researcher sudo && \
    passwd -d researcher && passwd -u researcher && \
    rm ~researcher/.bashrc ~researcher/.bash_logout ~researcher/.profile && \
    sed -i -e '/^PS1/s/^/#/' /etc/bash.bashrc && \
    sed -i -e '/stdout.*uname/s/^/#/' /etc/pam.d/login && \
    echo 'source /etc/profile.d/prompt.sh' >> /etc/bash.bashrc

# install Slicer extension; extension name hardcoded in install-slicer-extension.py
COPY files/install-slicer-extension.py /opt/slicer
# see https://github.com/pieper/SlicerDockers/blob/master/slicer-plus/Dockerfile
RUN su researcher -c "xvfb-run --auto-servernum \
    /opt/slicer/Slicer --python-script /opt/slicer/install-slicer-extension.py --no-splash --no-main-window"


#?? from SlicerDockers/blob/master/x11/Dockerfile
RUN echo "allowed_users=anybody" > /etc/X11/Xwrapper.config

# from SlicerDockers/blob/master/slicer/Dockerfile
RUN su researcher -c "mkdir /home/researcher/Documents"

#RUN mkdir -p /root/Desktop
#RUN ln -s /data /root/Desktop/
#WORKDIR /data

RUN mkdir -p /home/researcher/Desktop
RUN ln -s /kaapana/minio /home/researcher/Desktop/
WORKDIR /kaapana/minio

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/
