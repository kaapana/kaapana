FROM docker.io/cbioportal/cbioportal:5.3.7

LABEL IMAGE="cbioportal"
LABEL VERSION="5.3.7"
LABEL CI_IGNORE="False" 

RUN ["apt-get", "update"]
RUN ["apt-get", "install", "-y", "vim"]



COPY ./files/study/ /study
