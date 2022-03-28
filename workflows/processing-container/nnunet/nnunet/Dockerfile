FROM local-only/base-pytorch-gpu:0.1.0

LABEL IMAGE="nnunet"
LABEL VERSION="03-22"
LABEL CI_IGNORE="False"

ENV OMP_NUM_THREADS=1
ENV PYTHONUNBUFFERED=1

# nnUNet
ENV BRANCH=master
ENV NNUNET_VERSION=84b6389ae3362569cef0ff685bcb6bf24b64c693
RUN mkdir -p /nnunet-pip-package
RUN git clone  --single-branch --branch ${BRANCH} https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package && cd /nnunet-pip-package && git checkout ${NNUNET_VERSION}

RUN cd /nnunet-pip-package && pip3 install ./


COPY files/nnUNetTrainerV2.py /opt/conda/lib/python3.6/site-packages/nnunet/training/network_training/nnUNetTrainerV2.py
COPY files/nnUNetTrainer.py /opt/conda/lib/python3.6/site-packages/nnunet/training/network_training/nnUNetTrainer.py
COPY files/run_training.py /opt/conda/lib/python3.6/site-packages/nnunet/run/run_training.py
COPY files/predict.py /opt/conda/lib/python3.6/site-packages/nnunet/inference/predict.py
WORKDIR /executables/nnunet/
CMD ["bash","start_nnunet.sh"]
