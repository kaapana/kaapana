FROM local-only/base-python-gpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-nnunet-v2"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

# clone repo from tag v2.6.2 (commit: 74ceb6803d10dcee29b2cc481678d3a3d069f281; 02.06.2025)
ENV TAG=v2.6.2
RUN mkdir -p /nnunet-pip-package
RUN git clone --single-branch --branch ${TAG} https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package && cd /nnunet-pip-package

WORKDIR /nnunet-pip-package

# apply patches files
COPY files/patches_262/fingerprint_extractor_262.patch /nnunet-pip-package/
RUN git apply fingerprint_extractor_262.patch
COPY files/patches_262/nnUNetTrainer_262.patch /nnunet-pip-package/
RUN git apply nnUNetTrainer_262.patch
COPY files/patches_262/plan_and_preprocess_api_262.patch /nnunet-pip-package/
RUN git apply plan_and_preprocess_api_262.patch
COPY files/patches_262/plan_and_preprocess_entrypoints_262.patch /nnunet-pip-package/
RUN git apply plan_and_preprocess_entrypoints_262.patch
COPY files/patches_262/run_training_262.patch /nnunet-pip-package/
RUN git apply run_training_262.patch


# install pip package in editable mode
# RUN cd /nnunet-pip-package && pip3 install -e .

# install nnUNet pip package from source
RUN cd /nnunet-pip-package && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt ./
RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt tensorboard==2.15.1

WORKDIR /kaapana/app