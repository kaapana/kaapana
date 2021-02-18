FROM local-only/mitk-base:0.1.0 as build_container

LABEL IMAGE="mitk-flow"
LABEL VERSION="2021.02-vdev"
LABEL CI_IGNORE="False"

# =================================================================================================
# APPLICATION BUILD / EECUTABLE CREATION
# =================================================================================================

# Create application binary directories
RUN mkdir /opt/mitk-bin 
RUN mkdir /opt/bin

# MITK config
# https://phabricator.mitk.org/rMITK24935707b96301ba264664ac9735d64599611461
ENV MITK_BRANCH=master
ENV MITK_REV=24935707b96301ba264664ac9735d64599611461
# ENV MITK_REV=4bcb66b70182b06fcef1dcbd1f3e334b9b88 -> not existing

RUN git clone --single-branch --branch ${MITK_BRANCH} https://phabricator.mitk.org/source/mitk.git MITK && cd MITK && git checkout ${MITK_REV}

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

RUN mkdir -p /tmp_src /mitk
WORKDIR /tmp_src
COPY --from=build_container /opt/final_package/MITK-MitkFlow-linux-x86_64.tar.gz ./mitk.tar.gz
RUN tar -xzf mitk.tar.gz -C ./ && mv ./MITK-MitkFlow-linux-x86_64/* /mitk && rm -rf /tmp_src
  
# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /home/mitk/Desktop/
RUN chmod 0777 /home/mitk/Desktop/startMITK.sh
RUN ln -s /data /home/mitk/Desktop/
WORKDIR /data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/
