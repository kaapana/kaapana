FROM local-only/base-python-gpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-nnunet"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

ENV OMP_NUM_THREADS=1
ENV PYTHONUNBUFFERED=1
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True

# nnUNet
ENV BRANCH=master
ENV NNUNET_VERSION=84b6389ae3362569cef0ff685bcb6bf24b64c693
RUN mkdir -p /nnunet-pip-package
RUN git clone  --single-branch --branch ${BRANCH} https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package && cd /nnunet-pip-package && git checkout ${NNUNET_VERSION}

RUN cd /nnunet-pip-package && pip3 install ./

RUN pip install tensorboard==2.8.0

COPY files/patched/DatasetAnalyzer.py /usr/local/lib/python3.8/dist-packages/nnunet/experiment_planning/DatasetAnalyzer.py
COPY files/patched/network_trainer.py /usr/local/lib/python3.8/dist-packages/nnunet/training/network_training/network_trainer.py
COPY files/patched/nnUNet_plan_and_preprocess.py /usr/local/lib/python3.8/dist-packages/nnunet/experiment_planning/nnUNet_plan_and_preprocess.py
COPY files/patched/nnUNetTrainer.py /usr/local/lib/python3.8/dist-packages/nnunet/training/network_training/nnUNetTrainer.py
COPY files/patched/nnUNetTrainerV2.py /usr/local/lib/python3.8/dist-packages/nnunet/training/network_training/nnUNetTrainerV2.py
COPY files/patched/predict.py /usr/local/lib/python3.8/dist-packages/nnunet/inference/predict.py
COPY files/patched/run_training.py /usr/local/lib/python3.8/dist-packages/nnunet/run/run_training.py

WORKDIR /kaapana/app/