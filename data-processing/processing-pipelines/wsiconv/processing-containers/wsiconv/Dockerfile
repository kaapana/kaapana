FROM local-only/base-python-gpu:latest
LABEL IMAGE="wsiconv"
LABEL VERSION="1.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app
RUN apt-get update && \
    apt-get install -y \
    default-jre \
    unzip \
    nano \
    python3-pip \
    libtiff-tools \
    bc \
    dicom3tools \
    git \
    wget

RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt tifffile pydicom

RUN git clone https://github.com/ImagingDataCommons/idc-wsi-conversion.git

RUN curl https://www.kaapana.ai/kaapana-downloads/pixelmed-mirror/www.dclunie.com/pixelmed/software/20241027_current/pixelmed.jar -o pixelmed.jar && \
    curl https://www.kaapana.ai/kaapana-downloads/pixelmed-mirror/www.dclunie.com/pixelmed/software/20241027_current/pixelmedjavadicom_dependencyrelease.20241027.tar.bz2 -o pixelmedjavadicom_dependencyrelease.tar.bz2




RUN mkdir -p /kaapana/app/idc-wsi-conversion/pixelmed \
    && mkdir -p /kaapana/app/idc-wsi-conversion/jai_imageio \
    && mkdir -p /kaapana/app/idc-wsi-conversion/javax.json-1.0.4 \
    && mkdir -p /kaapana/app/idc-wsi-conversion/opencsv-2.4 \
    && mkdir -p /kaapana/app/Dependencies

RUN unzip pixelmed.jar -d /kaapana/app/idc-wsi-conversion/pixelmed/ \
    && unzip /kaapana/app/idc-wsi-conversion/jai_imageio.jar -d /kaapana/app/idc-wsi-conversion/jai_imageio \
    && unzip /kaapana/app/idc-wsi-conversion/javax.json-1.0.4.jar -d /kaapana/app/idc-wsi-conversion/javax.json-1.0.4 \
    && unzip /kaapana/app/idc-wsi-conversion/opencsv-2.4.jar -d /kaapana/app/idc-wsi-conversion/opencsv-2.4/ \
    && tar -xvjf pixelmedjavadicom_dependencyrelease.tar.bz2 -C /kaapana/app/Dependencies/ \
    && mv /kaapana/app/Dependencies/lib/ /kaapana/app/idc-wsi-conversion \
    && rm -r /kaapana/app/Dependencies \
    && rm -r /kaapana/app/idc-wsi-conversion/gdcsvstodcm.sh

RUN mv pixelmed.jar /kaapana/app/idc-wsi-conversion

COPY files/execute_svs.sh /kaapana/app
COPY files/gdcsvstodcm_svs.sh /kaapana/app/idc-wsi-conversion
COPY files/execute_tif.sh /kaapana/app
COPY files/gdcsvstodcm_tif.sh /kaapana/app/idc-wsi-conversion


RUN chmod +x /kaapana/app/idc-wsi-conversion/gdcsvstodcm_svs.sh \
    && chmod +x execute_svs.sh \
    && chmod +x /kaapana/app/idc-wsi-conversion/gdcsvstodcm_tif.sh \
    && chmod +x execute_tif.sh


ENTRYPOINT ["/bin/bash","-c","/kaapana/app/execute_tif.sh && /kaapana/app/execute_svs.sh"]
CMD ["/bin/bash"]


