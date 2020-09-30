FROM ubuntu:20.04 as build_container

LABEL IMAGE="mitk-fileconverter"
LABEL VERSION="1.1-vdev"
LABEL CI_IGNORE="False"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /opt

RUN apt-get update && apt-get install -y --no-install-recommends \
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
    file \
    && rm -rf /var/lib/apt/lists/*

ENV CMAKE_VERSION_A=3.16
ENV CMAKE_VERSION_B=3.16.4

# Install Cmake
RUN curl --silent --location -o cmake-installer.sh https://cmake.org/files/v${CMAKE_VERSION_A}/cmake-${CMAKE_VERSION_B}-Linux-x86_64.sh  \
    && mkdir /opt/cmake \
    && chmod +x cmake-installer.sh \
    && sh ./cmake-installer.sh --prefix=/opt/cmake --skip-license \
    && ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake \
    && rm cmake-installer.sh

# Shallow-clone latest master branch of MITK into MITK directory
ENV MITK_BRANCH=master
# master @ Tue Sep 1 16:36:16 2020 +0200
ENV MITK_COMMIT=96eff29e7367179328b5a7ff93e2b269e869f6bd
RUN git clone --single-branch --branch ${MITK_BRANCH} https://phabricator.mitk.org/source/mitk.git MITK && cd MITK && git checkout ${MITK_COMMIT}

# Generate Ninja build script for MITK to build a minimum configuration with apps in Release mode into MITK-superbuild directory
RUN cmake -S MITK -B MITK-superbuild -G Ninja -D CMAKE_BUILD_TYPE:STRING=Release -D MITK_BUILD_CONFIGURATION:STRING=CoreCmdApps -D MITK_CUSTOM_REVISION_DESC:STRING=FileConverter

# Build MITK superbuild and configure MITK build
RUN cmake --build MITK-superbuild --target MITK-Configure

# Build MitkFileConverter app
RUN cmake --build MITK-superbuild/MITK-build --target package 

RUN mkdir /opt/final_package
RUN cp -r /opt/MITK-superbuild/MITK-build/_CPack_Packages/Linux/TGZ/MITK-FileConverter-linux-x86_64 /opt/final_package

################################################################################################################################
###################################################### Final Container #########################################################
################################################################################################################################
FROM ubuntu:20.04

WORKDIR /opt

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglu1-mesa-dev \
    libxt-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build_container /opt/final_package/MITK-FileConverter-linux-x86_64 /opt/

ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR mitk-fileconverter

ENV CONVERTFROM dcm

# nrrd nii nii.gz
ENV CONVERTTO nrrd 
ENV FORCE_SINGLE_FILE false
ENV FILECONVERTER /opt/MitkFileConverter.sh

COPY files/mitk_fileconverter.sh /mitk_fileconverter.sh

CMD ["/bin/bash", "/mitk_fileconverter.sh"]

#  docker run --rm -it -e OPERATOR_IN_DIR="" -e CONVERTTO=nifti dktk-jip-registry.dkfz.de/public/mitk-fileconverter

