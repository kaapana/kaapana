FROM local-only/base-python-cpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-python-gpu"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

ARG CUDA_VERSION
LABEL com.nvidia.volumes.needed="nvidia_driver"
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV LD_LIBRARY_PATH /usr/local/nvidia/lib:/usr/local/nvidia/lib64

WORKDIR /kaapana/app
