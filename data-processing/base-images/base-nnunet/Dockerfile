FROM local-only/base-python-gpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-nnunet"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

# Unpatched nnU-Net, pinned to a master commit because nnFoundation (nnUNetv2_preprocess_like_nnssl,
# nnUNetv2_train_pretrained) is not in a release yet (latest: 2.8.1). Switch to the next release once it is out.
# The commit is recorded in every published unit (NNUNET_COMMIT).
ARG NNUNET_COMMIT=1489d746e084459581ff20382c1241d8cc2eb258
ENV NNUNET_COMMIT=${NNUNET_COMMIT}
ENV NNUNET_SRC=/opt/nnunet-src

# nnU-Net trains with torch.compile on GPU; Triton builds a small C extension at runtime and needs Python.h
RUN apt-get update -y && apt-get install -y --no-install-recommends python3.12-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/MIC-DKFZ/nnUNet.git ${NNUNET_SRC} \
    && git -C ${NNUNET_SRC} checkout ${NNUNET_COMMIT}

COPY --from=constraints 0.7.0.txt /constraints.txt
# huggingface_hub is imported by nnunetv2.experiment_planning.like_nnssl but not declared as a dependency
RUN pip3 install -c /constraints.txt ${NNUNET_SRC} huggingface_hub==0.36.2

WORKDIR /kaapana/app
