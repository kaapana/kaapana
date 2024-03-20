FROM docker.io/ubuntu:20.04 as build

LABEL IMAGE="ctp"
LABEL VERSION="0.1.3"
LABEL BUILD_IGNORE="False"

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
  git \
  openjdk-8-jdk \
  ant \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /build-ctp

RUN git clone -n https://github.com/johnperry/CTP.git . && git checkout 867f8933de7ce99a035a32639261a3af72ae91e0

COPY /files/Runner.java ./source/java/org/rsna/runner/
COPY /files/PCTable.java ./source/java/org/rsna/ctp/stdstages/dicom
# added consolelogs, to directly view logs in kubernetes logs
COPY /files/log4j.properties ./source/files/


# fixing: CVE-2021-23792  CVE-2021-35515 CVE-2021-37533
# some unused piplines (e.g. FtpExporter serivce) are untested with this fixes
# but are not used in kaapana
COPY /files/security-fix-libraries/commons-compress-1.25.0.jar ./libraries/
COPY /files/security-fix-libraries/commons-net-3.10.0.jar ./libraries/ftp
RUN rm -f ./libraries/commons-compress-1.0.jar
RUN rm -f ./libraries/imageio/twelvemonkeys-imageio-metadata-3.6-SNAPSHOT.jar
RUN rm -f ./libraries/ftp/commons-net-3.3.jar
COPY /files/security-fix-libraries/build.xml ./

# use java 8 for correct build process
ENV JAVA_HOME /usr/lib/jvm/java-1.8.0-openjdk-amd64 
RUN ant -buildfile build.xml

COPY /files/additional-libraries ./build/CTP/libraries

COPY /files/kaapana-dag-trigger ./build/kaapana-dag-trigger

RUN cd ./build/kaapana-dag-trigger \
  && ant -buildfile build.xml

#############################################################################################
###############################           2nd STAGE           ###############################
#############################################################################################

FROM local-only/base-python-cpu:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
  default-jre \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/CTP

COPY /files/config.xml ./config.xml
COPY --from=build /build-ctp/build/CTP/ ./

CMD ["java","-jar","Runner.jar"]


