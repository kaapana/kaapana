FROM ubuntu:20.04

LABEL IMAGE="mitk-fileconverter"
LABEL VERSION="25.01.2021-vdev"
LABEL CI_IGNORE="False"

WORKDIR /opt

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglu1-mesa-dev \
    libxt-dev \
    libgomp1 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
ADD https://www.mitk.org/download/ci/snapshots/Ubuntu%2018.04/MITK-snapshots_2021-01-25-linux-x86_64.tar.gz /src/mitk.tar.gz
RUN tar -xzf /src/mitk.tar.gz --strip 1 -C /opt/ && rm -rf /src/mitk.tar.gz

ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR mitk-fileconverter

ENV CONVERTFROM dcm

# nrrd nii nii.gz
ENV CONVERTTO nrrd 
ENV FORCE_SINGLE_FILE false
ENV FILECONVERTER /opt/MitkFileConverter.sh

COPY files/mitk_fileconverter.sh /mitk_fileconverter.sh

CMD ["/bin/bash", "/mitk_fileconverter.sh"]

#  docker run --rm -it -e OPERATOR_IN_DIR="" -e CONVERTTO=nifti dktk-jip-registry.dkfz.de/public/mitk-fileconverter
