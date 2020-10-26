FROM ubuntu:20.04 as build

LABEL IMAGE=ctp
LABEL VERSION=0.1.1
LABEL CI_IGNORE=False

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
    git \
    openjdk-8-jdk \
    ant

WORKDIR /build-ctp

RUN git clone -n https://github.com/johnperry/CTP.git .
# use util FROM newer commit (a bugfix for dicomweb is needed)

RUN git checkout 774d7be96d12164babfe04a875adf603223886a8
RUN cp ./libraries/util.jar /tmp/ \
 && git checkout tags/x101 \
 && mv /tmp/util.jar ./libraries/util.jar

# use java 8 for correct build process
ENV JAVA_HOME /usr/lib/jvm/java-1.8.0-openjdk-amd64 
RUN ant -buildfile build.xml

ADD /files/additional-libraries ./build/CTP//libraries

ADD /files/kaapana-dag-trigger ./build/kaapana-dag-trigger
RUN cd ./build/kaapana-dag-trigger \
  && ant -buildfile build.xml

ADD /files/ctp_api_pseudonymization ./build/ctp_api_pseudonymization
RUN cd ./build/ctp_api_pseudonymization \
  && ant -buildfile build.xml

#############################################################################################
###############################           2nd STAGE           ###############################
#############################################################################################


FROM ubuntu:20.04


RUN apt-get update && apt-get install -y \
    default-jre \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/CTP

ADD /files/config.xml ./config.xml
COPY --from=build /build-ctp/build/CTP/ ./

CMD ["java","-jar","Runner.jar"]

