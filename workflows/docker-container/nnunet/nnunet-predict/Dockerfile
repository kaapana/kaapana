FROM nvcr.io/nvidia/pytorch:20.08-py3
# FROM pytorch/pytorch:latest

LABEL IMAGE="nnunet-predict"
LABEL VERSION="0.2-vdev"
LABEL CI_IGNORE="False"

RUN mkdir /nnunet
ENV nnUNet_raw_data_base="/nnunet"
ENV nnUNet_preprocessed="/nnUNet_preprocessed"
RUN mkdir /nnunet/nnUNet_preprocessed
RUN mkdir /models
ENV RESULTS_FOLDER="/models"
ENV MODEL="2d"
ENV MODE="predict"
ENV PREP_DIR="nnunet-prep"
ENV PREPARATION="true"

RUN apt-get update && apt-get install -y \
    git \
 && rm -rf /var/lib/apt/lists/*

RUN pip install 'pillow<7.1' --force-reinstall
RUN pip install --upgrade git+https://github.com/nanohanno/hiddenlayer.git@bugfix/get_trace_graph#egg=hiddenlayer

RUN mkdir /src

WORKDIR /src
COPY files/requirements.txt /src
RUN pip install -r /src/requirements.txt

RUN mkdir /nnunet-pip-package
RUN git clone https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package

RUN cd /nnunet-pip-package && pip install ./

COPY files/ /src
 

CMD ["bash","/src/start.sh"]