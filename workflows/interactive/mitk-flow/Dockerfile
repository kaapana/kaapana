FROM local-only/mitk-base:0.1.0 as build_container

LABEL IMAGE="mitk-flow"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

# =================================================================================================
# APPLICATION BUILD / EXECUTABLE CREATION
# =================================================================================================

# Create application binary directories
RUN mkdir /opt/mitk-bin 
RUN mkdir /opt/bin

# MITK config
ENV MITK_BRANCH=master
# ENV MITK_REV=4bcb66b70182b06fcef1dcbd1f3e334b9b88 -> not existing

RUN git clone --single-branch --branch ${MITK_BRANCH} https://phabricator.mitk.org/source/mitk.git MITK && cd MITK 
# && git checkout ${MITK_REV}

# Generate Ninja build script for MITK to build a minimum configuration with apps in Release mode into MITK-superbuild directory
RUN cmake -G Ninja -S MITK -B MITK-superbuild
RUN cmake -S MITK -B MITK-superbuild -D CMAKE_BUILD_TYPE:STRING=Release -D BUILD_TESTING:BOOL=OFF -D MITK_BUILD_CONFIGURATION:STRING=FlowBenchSegmentationRelease -D MITK_CUSTOM_REVISION_DESC:STRING=MitkFlow

RUN git config --global url.https://github.com/.insteadOf git://github.com/
# Build MITK superbuild and configure MITK build
RUN cmake --build MITK-superbuild

# Build MitkFileConverter app
RUN cmake --build MITK-superbuild/MITK-build --target package 

RUN mkdir /opt/final_package
RUN cp /opt/MITK-superbuild/MITK-build/MITK-MitkFlow-linux-x86_64.tar.gz /opt/final_package/MITK-MitkFlow-linux-x86_64.tar.gz

#############################################################################################
###############################           2nd STAGE           ###############################
#############################################################################################

FROM local-only/no-vnc-base:0.1.0

RUN apt-get update && apt-get install -q -y --no-install-recommends \
    build-essential \
    git \
    libglu1-mesa-dev \
    libtiff5-dev \
    libwrap0-dev \
    libxcomposite1 \
    libxcursor1 \
    libxi-dev \
    libxkbcommon-x11-0 \
    libxt-dev \
    mesa-common-dev \
    ca-certificates \
    curl \
    ninja-build \
    libasound2 \
    libnss3-dev \
    libnss3 \
    libnspr4-dev \
    libxtst6 \
    file \
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
    libfontconfig1-dev \ 
    libdbus-1-3 \
    doxygen \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get -y update && apt-get -y install \
    ca-certificates \
    libglu1-mesa-dev \
    libtiff5-dev \
    libwrap0-dev \
    libxcomposite1 \
    libxcursor1 \
    libxi-dev \
    libxkbcommon-x11-0 \
    libxt-dev \
    mesa-common-dev \
    libssl-dev \
    wmctrl \
    at-spi2-core  \
    gedit \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp_src /mitk
WORKDIR /tmp_src
COPY --from=build_container /opt/final_package/MITK-MitkFlow-linux-x86_64.tar.gz ./mitk.tar.gz
RUN tar -xzf mitk.tar.gz -C ./ && mv ./MITK-MitkFlow-linux-x86_64/* /mitk && rm -rf /tmp_src

WORKDIR /mitk
    
# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /home/mitk/Desktop/
RUN chmod 0777 /home/mitk/Desktop/startMITK.sh

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/
