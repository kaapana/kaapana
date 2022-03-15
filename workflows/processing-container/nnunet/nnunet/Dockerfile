FROM nvcr.io/nvidia/pytorch:20.09-py3

LABEL IMAGE="nnunet"
LABEL VERSION="04-21"
LABEL CI_IGNORE="False"

ENV OMP_NUM_THREADS=1
ENV PYTHONUNBUFFERED=1

ENV BRANCH=master
ENV NNUNET_VERSION=a7d1d875e8fc3f4e93ca7b51b1ba206711844d92

RUN apt-get update && apt-get install -y \
    git \
    htop \
    zip \
    unzip \
 && rm -rf /var/lib/apt/lists/*

RUN pip install 'pillow<7.1' --force-reinstall
RUN pip install --upgrade git+https://github.com/nanohanno/hiddenlayer.git@bugfix/get_trace_graph#egg=hiddenlayer

RUN mkdir /src

WORKDIR /src
COPY files/requirements.txt /src
RUN pip install -r /src/requirements.txt

RUN mkdir /nnunet-pip-package
RUN git clone  --single-branch --branch ${BRANCH} https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package && cd /nnunet-pip-package && git checkout ${NNUNET_VERSION}

RUN cd /nnunet-pip-package && pip install ./

RUN pip install batchgenerators==0.21 # should be removed some day...
COPY files/ /src

# COPY files/nnUNetTrainerV2.py /opt/conda/lib/python3.6/site-packages/nnunet/training/network_training/nnUNetTrainerV2.py
# COPY files/run_training.py /opt/conda/lib/python3.6/site-packages/nnunet/run/run_training.py
# COPY files/predict.py /opt/conda/lib/python3.6/site-packages/nnunet/inference/predict.py

COPY files/patches/nnUNetTrainerV2.py /opt/conda/lib/python3.6/site-packages/nnunet/training/network_training/nnUNetTrainerV2.py
COPY files/patches/nnUNetTrainer.py /opt/conda/lib/python3.6/site-packages/nnunet/training/network_training/nnUNetTrainer.py
COPY files/patches/run_training.py /opt/conda/lib/python3.6/site-packages/nnunet/run/run_training.py
COPY files/patches/predict.py /opt/conda/lib/python3.6/site-packages/nnunet/inference/predict.py

CMD ["bash","/src/start_nnunet.sh"]
