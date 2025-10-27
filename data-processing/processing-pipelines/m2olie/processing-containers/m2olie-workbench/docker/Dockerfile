FROM local-only/base-desktop:latest

LABEL IMAGE="m2olie-workbench"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"
ENV ELASTIX_VERSION="5.0.0"

RUN mkdir -p /src

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /m2olie \
    && wget --no-check-certificate https://kaapana.ai/kaapana-downloads/m2olie/mitk-elastix-20231031_22-04_linux-x86_64.tar.gz -O /m2olie/elastix.tar.gz \
    && tar -xzf /m2olie/elastix.tar.gz --strip 1 -C /m2olie/ \
    && rm -rf /m2olie/elastix.tar.gz

RUN wget --no-check-certificate https://github.com/SuperElastix/elastix/releases/download/${ELASTIX_VERSION}/elastix-${ELASTIX_VERSION}-linux.tar.bz2 -O /src/elastix.tar.bz2 \
    && tar -xjf /src/elastix.tar.bz2 --strip 1 -C /m2olie/ \
    && rm -rf /src/elastix.tar.bz2

COPY files/startMITK.sh /m2olie/

RUN ln -s /data /home/$USER/Desktop/
WORKDIR /data

# $OPERATOR_IN_DIR_FIXED/*.nrrd
# $OPERATOR_IN_DIR_FIXED/*.nii
# $OPERATOR_IN_DIR_FIXED/*.dcm
ENV OPERATOR_IN_DIR_FIXED=fixed-input

# expected input files in OPERATOR_IN_DIR_MOVING
# $OPERATOR_IN_DIR_FIXED/*.nrrd
# $OPERATOR_IN_DIR_FIXED/*.nii
# $OPERATOR_IN_DIR_FIXED/*.dcm
ENV OPERATOR_IN_DIR_MOVING=moving-input

# expected outut files in OPERATOR_OUT_DIR
# OPERATOR_OUT_DIR/result.0.nrrd (*)
# OPERATOR_OUT_DIR/TransformParameters.0.txt (*)
# OPERATOR_OUT_DIR/TransformParameters.1.txt (*)
# OPERATOR_OUT_DIR/elastix.log
ENV OPERATOR_OUT_DIR=registration


COPY files/supervisord-m2olie.conf /etc/supervisor/conf.d/

