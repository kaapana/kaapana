FROM local-only/base-python-gpu:latest
LABEL IMAGE="wsiconv"
LABEL VERSION="1.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
Run mkdir Data
RUN apt-get update
RUN apt install -y default-jre  
RUN apt-get install -y unzip
RUN apt-get install nano
RUN apt-get install -y python3-pip
RUN apt-get install -y libtiff-tools
RUN apt-get install -y bc
#RUN apt-get install -y openjdk-8-jdk
#RUN apt-get install -y openjdk-8-jre
RUN apt-get install -y dicom3tools
RUN pip install tifffile
RUN pip install pydicom
RUN apt-get -y install git
RUN git clone https://github.com/ImagingDataCommons/idc-wsi-conversion.git
RUN apt install wget
RUN wget http://www.dclunie.com/pixelmed/software/20221004_current/pixelmed.jar
RUN wget http://www.dclunie.com/pixelmed/software/20221004_current/pixelmedjavadicom_dependencyrelease.20221004.tar.bz2




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
RUN mkdir -p /kaapana/app/idc-wsi-conversion/Data

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


