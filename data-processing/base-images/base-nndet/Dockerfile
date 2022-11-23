FROM nvcr.io/nvidia/pytorch:20.12-py3
# Contains pytorch, torchvision, cuda, cudnn

#FROM local-only/base-python-gpu:latest
# Error: torchtext-legacy not found


LABEL REGISTRY="local-only"
LABEL IMAGE="base-nndet"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

# nndet
ENV BRANCH=main
RUN mkdir -p /nndet-pip-package
RUN git clone --single-branch --branch ${BRANCH} https://github.com/MIC-DKFZ/nnDetection.git /nndet-pip-package

# Setup environment variables
ENV det_num_threads=6 det_verbose=1 OMP_NUM_THREADS=1

# Install some tools
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive && apt-get install -y \
 git \
 cmake \
 make \
 wget \
 gnupg \
 build-essential \
 software-properties-common \
 gdb \
 ninja-build

# updating requests and urllib3 fixed compatibility with my docker version
RUN pip install numpy \
  && pip install --upgrade requests \
  && pip install --upgrade urllib3 \
  && pip install packaging==21.00

RUN pip install hydra-core --upgrade --pre \
  && pip install git+https://github.com/mibaumgartner/pytorch_model_summary.git

# Install own code
RUN cd /nndet-pip-package \
  && pip install -r requirements.txt \
  && FORCE_CUDA=1 pip install -v -e .

WORKDIR /kaapanasrc/

# Code server
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

# data & model dir
ENV det_data=/det_data det_models=/models/nnDet

RUN mkdir ${det_data} \
  && mkdir -p ${det_models}