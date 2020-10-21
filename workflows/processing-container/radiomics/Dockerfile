FROM local-only/mitk-base:0.1.0 as build_container

LABEL IMAGE="mitk-radiomics"
LABEL VERSION="15.10.20-master"
LABEL CI_IGNORE="False"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /opt
    
# Shallow-clone latest master branch of MITK into MITK directory
ENV MITK_BRANCH=master
# master @ Thu, Oct 15, 2020
ENV MITK_REV=0f33cec9e310
RUN git clone --single-branch --branch ${MITK_BRANCH} https://phabricator.mitk.org/source/mitk.git MITK && cd MITK && git checkout ${MITK_REV}

# Generate Ninja build script for MITK to build a minimum configuration with apps in Release mode into MITK-superbuild directory
RUN cmake -G Ninja -S MITK -B MITK-superbuild
RUN cmake -S MITK -B MITK-superbuild -D CMAKE_BUILD_TYPE:STRING=Release -D MITK_BUILD_CONFIGURATION:STRING=ClassificationCmdApps -D MITK_CUSTOM_REVISION_DESC:STRING=Radiomics

RUN git config --global url.https://github.com/.insteadOf git://github.com/
# Build MITK superbuild and configure MITK build
RUN cmake --build MITK-superbuild

# Build MitkFileConverter app
RUN cmake --build MITK-superbuild/MITK-build --target package 

RUN mkdir /opt/final_package
RUN cp /opt/MITK-superbuild/MITK-build/MITK-Radiomics-linux-x86_64.tar.gz /opt/final_package/MITK-Radiomics-linux-x86_64.tar.gz

################################################################################################################################
###################################################### Final Container #########################################################
################################################################################################################################
FROM ubuntu:20.04

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglu1-mesa-dev \
    libxt-dev \
    libgomp1 \
    xvfb \
    qtbase5-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp_src /mitk
WORKDIR /tmp_src
COPY --from=build_container /opt/final_package/MITK-Radiomics-linux-x86_64.tar.gz ./MITK-Radiomics-linux-x86_64.tar.gz
RUN tar -xzf MITK-Radiomics-linux-x86_64.tar.gz -C ./ && mv ./MITK-Radiomics-linux-x86_64/* /mitk && rm -rf /tmp_src

WORKDIR /
ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR radiomics

COPY files/radiomics.sh /

CMD ["/bin/bash", "/radiomics.sh"]
