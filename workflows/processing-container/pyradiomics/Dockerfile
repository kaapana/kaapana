FROM ubuntu:20.04

LABEL IMAGE="pyradiomics-init"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="True"

USER root
RUN apt-get update
RUN apt-get -y install python3.8
RUN apt-get -y install make curl cmake>=3.16.3 gcc g++ 
RUN apt-get -y install subversion python3-dev git>=1.65
RUN apt-get -y install python3-pip 

RUN python3 -m pip install --upgrade pip==20.0.2
RUN python3 -m pip install --upgrade setuptools wheel
RUN echo $(pip --version)
RUN echo $(python3 --version)

RUN python3 -m pip install numpy
RUN python3 -m pip install scikit-build
RUN python3 -m pip -v install SimpleITK==2.1.1

#RUN ITK_USE_GIT_PROTOCOL="https"
#RUN echo $ITK_USE_GIT_PROTOCOL
RUN python3 -m pip -v install pyradiomics==3.0.1

COPY pyradiomics_init.py /

CMD ["python3","-u","/pyradiomics_init.py"]