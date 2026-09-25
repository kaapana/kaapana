FROM local-only/base-python-cpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-gpu"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

ARG CUDA_VERSION
LABEL com.nvidia.volumes.needed="nvidia_driver"
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV LD_LIBRARY_PATH /usr/local/nvidia/lib:/usr/local/nvidia/lib64

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install torch for cuda 11.8. Only here, not in base-python-cpu: the CUDA build is
# most of that image's size, and CPU-only workflows never load it.
RUN pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu118

# Copy and install kaapana_federated directly from source (imports torch)
COPY files/kaapana_federated /app/kaapana_federated
RUN python3 -m pip install /app/kaapana_federated

WORKDIR /kaapana/app
