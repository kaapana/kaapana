# FROM nvidia/cuda:10.2-runtime-ubuntu18.04
#FROM nvcr.io/nvidia/pytorch:20.09-py3
FROM nvcr.io/nvidia/pytorch:22.02-py3

LABEL REGISTRY="local-only"
LABEL IMAGE="base-pytorch-gpu"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apt-get update

# Only for jupyternotebook: jupyter nbconvert --to html --no-input ...
ENV TZ=Europe
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get install -y texlive-xetex texlive-fonts-recommended texlive-plain-generic

RUN apt-get update && apt-get install -y \
    git \
    htop \
    zip \
    unzip \
 && rm -rf /var/lib/apt/lists/*

# Common Python packages
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

COPY files/run.sh /root/

CMD ["/bin/bash", "/root/run.sh"]