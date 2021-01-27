FROM local-only/mitk-base:0.1.0 as build_container

LABEL IMAGE="mitk-fileconverter"
LABEL VERSION="25.01.2021-develop"
LABEL CI_IGNORE="False"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /opt

# Shallow-clone latest master branch of MITK into MITK directory
ENV MITK_BRANCH=develop
# develop @ 25.01.2021 
ENV MITK_COMMIT=3ec0dd08e0e6e69d38be4f64161e037b15d3e498
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
    libfreetype6 \
    libgtk2.0-0:i386 \
    libidn11:i386 \
    libglu1-mesa:i386 \
    libpangox-1.0-0:i386 \ 
    libpangoxft-1.0-0:i386 \
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

