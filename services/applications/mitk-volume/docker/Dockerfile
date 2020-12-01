FROM local-only/mitk-base:0.1.0 as build_container

LABEL IMAGE="mitk-volume"
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
ENV MITK_REV=0f33cec9e310c3f69b6c46795f29c026f7e90dc6

RUN git clone --single-branch --branch ${MITK_BRANCH} https://phabricator.mitk.org/source/mitk.git MITK && cd MITK && git checkout ${MITK_REV}

# Generate Ninja build script for MITK to build a minimum configuration with apps in Release mode into MITK-superbuild directory
RUN cmake -G Ninja -S MITK -B MITK-superbuild
RUN cmake -S MITK -B MITK-superbuild -D CMAKE_BUILD_TYPE:STRING=Release -D BUILD_TESTING:BOOL=OFF -D MITK_CUSTOM_REVISION_DESC:STRING=MitkVolume

RUN git config --global url.https://github.com/.insteadOf git://github.com/
# Build MITK superbuild and configure MITK build
RUN cmake --build MITK-superbuild

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
