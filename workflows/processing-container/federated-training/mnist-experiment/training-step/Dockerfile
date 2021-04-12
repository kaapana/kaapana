#TODO: more lean base image
#FROM python:3.9-alpine3.12 
FROM pytorchlightning/pytorch_lightning:base-cuda-py3.7-torch1.7

LABEL IMAGE="testing"
LABEL VERSION="0.1.0-vdev"
LABEL CI_IGNORE="True"

WORKDIR /

COPY files/* /

#CMD tail -f  /dev/null
CMD ["python3","-u","/process.py"]