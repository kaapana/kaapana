FROM local-only/base-python-gpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-nnunet-v2"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

# nnUNet
# # Option 1: Clone repo from commit 2eaa371317c55e22bf5166428315076a1ba9b7af (21.06.2024)
# ENV BRANCH=master
# ENV NNUNET_VERSION=2eaa371317c55e22bf5166428315076a1ba9b7af
# RUN mkdir -p /nnunet-pip-package
# RUN git clone  --single-branch --branch ${BRANCH} https://github.com/MIC-DKFZ/nnUNet.git /nnunet-pip-package && cd /nnunet-pip-package && git checkout ${NNUNET_VERSION}
# # patched files
# Option 2: Install nnunetv2 pip package
WORKDIR /app
COPY files/requirements.txt /app/
RUN python -m pip install --upgrade setuptools pip && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /app/requirements.txt

# Kaapana
# RUN cd /nnunet-pip-package && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt ./
# RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt tensorboard==2.15.1

WORKDIR /kaapana/app