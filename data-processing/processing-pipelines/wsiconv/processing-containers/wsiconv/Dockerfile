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

RUN wget http://www.dclunie.com/pixelmed/software/20221004_old/pixelmed.jar && \
    wget http://www.dclunie.com/pixelmed/software/20221004_old/pixelmedjavadicom_dependencyrelease.20221004.tar.bz2




RUN mkdir -p /kaapana/app/idc-wsi-conversion/pixelmed
RUN mkdir -p /kaapana/app/idc-wsi-conversion/jai_imageio
RUN mkdir -p /kaapana/app/idc-wsi-conversion/javax.json-1.0.4
RUN mkdir -p /kaapana/app/idc-wsi-conversion/opencsv-2.4
RUN mkdir -p /kaapana/app/Dependencies

RUN unzip pixelmed.jar -d /kaapana/app/idc-wsi-conversion/pixelmed/


RUN unzip /kaapana/app/idc-wsi-conversion/jai_imageio.jar -d /kaapana/app/idc-wsi-conversion/jai_imageio
RUN unzip /kaapana/app/idc-wsi-conversion/javax.json-1.0.4.jar -d /kaapana/app/idc-wsi-conversion/javax.json-1.0.4
RUN unzip /kaapana/app/idc-wsi-conversion/opencsv-2.4.jar -d /kaapana/app/idc-wsi-conversion/opencsv-2.4/
RUN tar -xvjf pixelmedjavadicom_dependencyrelease.20221004.tar.bz2 -C /kaapana/app/Dependencies/
RUN mv /kaapana/app/Dependencies/lib/ /kaapana/app/idc-wsi-conversion
RUN rm -r /kaapana/app/Dependencies
RUN rm -r /kaapana/app/idc-wsi-conversion/gdcsvstodcm.sh

RUN mv pixelmed.jar /kaapana/app/idc-wsi-conversion

COPY files/execute_svs.sh /kaapana/app
COPY files/gdcsvstodcm_svs.sh /kaapana/app/idc-wsi-conversion
COPY files/execute_tif.sh /kaapana/app
COPY files/gdcsvstodcm_tif.sh /kaapana/app/idc-wsi-conversion


RUN chmod +x /kaapana/app/idc-wsi-conversion/gdcsvstodcm_svs.sh
RUN chmod +x execute_svs.sh
RUN chmod +x /kaapana/app/idc-wsi-conversion/gdcsvstodcm_tif.sh
RUN chmod +x execute_tif.sh



ENTRYPOINT ["/bin/bash","-c","/kaapana/app/execute_tif.sh && /kaapana/app/execute_svs.sh"]
CMD ["/bin/bash"]


