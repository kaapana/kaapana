# FROM nvidia/cuda:10.2-runtime-ubuntu18.04
FROM nvcr.io/nvidia/pytorch:20.09-py3

LABEL REGISTRY="local-only"
LABEL IMAGE="base-pytorch"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apt-get update

# Only for jupyternotebook: jupyter nbconvert --to html --no-input ...
ENV TZ=Europe
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get install -y texlive-xetex texlive-fonts-recommended texlive-plain-generic

# Common Python packages
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

# nnUNet
ENV BRANCH=master
ENV NNUNET_VERSION=a7d1d875e8fc3f4e93ca7b51b1ba206711844d92
RUN mkdir -p /nnunet-pip-package
RUN git clone  --single-branch --branch ${BRANCH} https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package && cd /nnunet-pip-package && git checkout ${NNUNET_VERSION}

RUN cd /nnunet-pip-package && pip install ./

RUN pip install batchgenerators==0.21 # should be removed some day...


COPY files/run.sh /root/

CMD ["/bin/bash", "/root/run.sh"]