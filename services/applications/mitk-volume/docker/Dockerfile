FROM local-only/mitk-base:0.1.0 as build_container

LABEL IMAGE="mitk-volume"
LABEL VERSION="2020-12-01-vdev"
LABEL CI_IGNORE="False"

# =================================================================================================
# APPLICATION BUILD / EXECUTABLE CREATION
# =================================================================================================
# Create application binary directories
RUN mkdir /opt/mitk-bin 
RUN mkdir /opt/bin

# MITK config
# 01.12.20 develop
ENV MITK_BRANCH=develop
ENV MITK_REV=7cdad74bd60adc8c32a00979a4ae96839e273076  

RUN git clone --single-branch --branch ${MITK_BRANCH} https://phabricator.mitk.org/source/mitk.git MITK && cd MITK && git checkout ${MITK_REV}

# Generate Ninja build script for MITK to build a minimum configuration with apps in Release mode into MITK-superbuild directory
RUN cmake -G Ninja -S MITK -B MITK-superbuild
RUN cmake -S MITK -B MITK-superbuild -D CMAKE_BUILD_TYPE:STRING=Release -D BUILD_TESTING:BOOL=OFF -D MITK_CUSTOM_REVISION_DESC:STRING=MitkVolume

RUN git config --global url.https://github.com/.insteadOf git://github.com/
# Build MITK superbuild and configure MITK build
RUN cmake --build MITK-superbuild

RUN cmake -S MITK -B MITK-superbuild/MITK-build \
            -D MITK_BUILD_org.mitk.gui.qt.segmentation:Bool=ON 
# Build MitkFileConverter app
RUN cmake --build MITK-superbuild/MITK-build --target package 

#-D MITK_BUILD_org.mitk.gui.qt.measurementtoolbox:Bool=OFF -D MITK_BUILD_org.mitk.gui.qt.segmentation:Bool=ON 

RUN mkdir /opt/final_package
RUN cp /opt/MITK-superbuild/MITK-build/MITK-MitkVolume-linux-x86_64.tar.gz /opt/final_package/MITK-MitkVolume-linux-x86_64.tar.gz

#############################################################################################
###############################           2nd STAGE           ###############################
#############################################################################################
FROM local-only/no-vnc-base:0.1.0

RUN mkdir -p /tmp_src /mitk
WORKDIR /tmp_src
COPY --from=build_container /opt/final_package/MITK-MitkVolume-linux-x86_64.tar.gz ./mitk.tar.gz
RUN tar -xzf mitk.tar.gz -C ./ && mv ./MITK-MitkVolume-linux-x86_64/* /mitk && rm -rf /tmp_src

# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startMITK.sh
RUN ln -s /data /root/Desktop/
WORKDIR /data
RUN mkdir /root/Desktop/test-data
# COPY files/Pic3D.nrrd /root/Desktop/test-data

# A supervisord config is used to make the application managed
COPY files/supervisord.conf /etc/supervisor/conf.d/
