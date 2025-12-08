# WARNING: THIS DOCKERFILE IS DEPRECATED AND WILL BE REMOVED IN FUTURE RELEASES!
# PLEASE USE THE MAINTAINED BASE IMAGE INSTEAD: `data-processing/base-images/base-python-gpu/Dockerfile`

FROM local-only/base-python-cpu-3.10:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-gpu-3.10"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

ARG CUDA_VERSION
LABEL com.nvidia.volumes.needed="nvidia_driver"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.10/dist-packages/torch/lib:/usr/local/lib/python3.10/dist-packages/torch_tensorrt/lib:/usr/local/cuda/compat/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /kaapana/app
