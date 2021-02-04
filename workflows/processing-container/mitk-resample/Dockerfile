FROM local-only/mitk-base:0.1.0 as build_container

LABEL IMAGE="mitk-resample"
LABEL VERSION="04.02.2021-develop"
LABEL CI_IGNORE="False"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /opt

# Shallow-clone latest master branch of MITK into MITK directory
ENV MITK_BRANCH=develop
# develop @ Tue Feb 4 2021
ENV MITK_COMMIT=ae90d3d48c7b5517c9b4a0134304e11c1fcac5af
RUN git clone --single-branch --branch ${MITK_BRANCH} https://phabricator.mitk.org/source/mitk.git MITK && cd MITK && git checkout ${MITK_COMMIT}

# Generate Ninja build script for MITK to build a minimum configuration with apps in Release mode into MITK-superbuild directory
RUN cmake -S MITK -B MITK-superbuild -G Ninja -D CMAKE_BUILD_TYPE:STRING=Release -D MITK_BUILD_CONFIGURATION:STRING=PhenotypingRelease -D MITK_CUSTOM_REVISION_DESC:STRING=MitkReample

# Build MITK superbuild and configure MITK build
RUN cmake --build MITK-superbuild --target MITK-Configure

# Build MitkFileConverter app
RUN cmake --build MITK-superbuild/MITK-build --target package 

RUN mkdir /opt/final_package
RUN cp -r /opt/MITK-superbuild/MITK-build/_CPack_Packages/Linux/TGZ/MITK-MitkReample-linux-x86_64 /opt/final_package

################################################################################################################################
###################################################### Final Container #########################################################
################################################################################################################################
FROM ubuntu:20.04

WORKDIR /opt

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglu1-mesa-dev \
    libgomp1 \
    libxt-dev \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build_container /opt/final_package/MITK-MitkReample-linux-x86_64 /opt/

ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR mitk-resample

COPY files/MitkCLResampleImageToReference.sh /opt/MitkCLResampleImageToReference.sh
ENV EXECUTABLE /opt/MitkCLResampleImageToReference.sh

COPY files/start.sh /start.sh
CMD ["/bin/bash", "/start.sh"]

#  docker run --rm -it -e OPERATOR_IN_DIR="" -e CONVERTTO=nifti dktk-jip-registry.dkfz.de/public/mitk-fileconverter