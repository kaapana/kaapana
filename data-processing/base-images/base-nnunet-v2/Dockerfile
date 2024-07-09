FROM local-only/base-python-gpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-nnunet-v2"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

# nnUNet

# Option 1: Clone repo from tag v2.4.2 (commit: 65bad9df96e399efd53805c7739a8e05144be5f4; 25.04.2024)
ENV TAG=v2.4.2
RUN mkdir -p /nnunet-pip-package
RUN git clone --single-branch --branch ${TAG} https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package && cd /nnunet-pip-package
# RUN git clone --single-branch --branch ${BRANCH} https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package && cd /nnunet-pip-package && git checkout ${NNUNET_VERSION}
# patched files
WORKDIR /nnunet-pip-package
COPY files/patched/plan_and_preprocess_entrypoints.patch /nnunet-pip-package/
RUN git apply plan_and_preprocess_entrypoints.patch
COPY files/patched/plan_and_preprocess_api.patch /nnunet-pip-package/
RUN git apply plan_and_preprocess_api.patch
COPY files/patched/nnUNetTrainer.patch /nnunet-pip-package/
RUN git apply nnUNetTrainer.patch
COPY files/patched/run_training.patch /nnunet-pip-package/
RUN git apply run_training.patch

# install pip package in editable/dev mode
RUN cd /nnunet-pip-package && pip3 install -e .

# # Option 2: Install nnunetv2 pip package
# WORKDIR /app
# COPY files/requirements.txt /app/
# RUN python -m pip install --upgrade setuptools pip && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /app/requirements.txt

# Kaapana
RUN cd /nnunet-pip-package && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt ./
RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt tensorboard==2.15.1

WORKDIR /kaapana/app