FROM local-only/base-python-cpu:latest

LABEL IMAGE="m2olie-elastix-registration"
LABEL VERSION="2023-10-10"
LABEL CI_IGNORE="False"
ENV ELASTIX_VERSION="5.0.0"

RUN mkdir -p /src

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

#RUN wget --no-check-certificate https://github.com/SuperElastix/elastix/releases/download/${ELASTIX_VERSION}/elastix-${ELASTIX_VERSION}-linux.tar.bz2 -O /src/elastix.tar.bz2
RUN wget --no-check-certificate https://data.jtfc.de/mitk-elastix-v2.tar.gz -O /src/elastix.tar.bz
RUN tar -xvf /src/elastix.tar.bz -C /usr/ && rm -rf /src/elastix.tar.bz

WORKDIR /

# This container expects two input folders 
# OPERATOR_IN_DIR_FIXED and OPERATOR_IN_DIR_MOVING

# expected input files in OPERATOR_IN_DIR_FIXED
# $OPERATOR_IN_DIR_FIXED/*.nrrd
# $OPERATOR_IN_DIR_FIXED/*.nii
# $OPERATOR_IN_DIR_FIXED/*.dcm
ENV OPERATOR_IN_DIR_FIXED fixed-input

# expected input files in OPERATOR_IN_DIR_MOVING
# $OPERATOR_IN_DIR_FIXED/*.nrrd
# $OPERATOR_IN_DIR_FIXED/*.nii
# $OPERATOR_IN_DIR_FIXED/*.dcm
ENV OPERATOR_IN_DIR_MOVING moving-input

# expected outut files in OPERATOR_OUT_DIR
# OPERATOR_OUT_DIR/result.0.nrrd (*)
# OPERATOR_OUT_DIR/result.1.nrrd (*)
# OPERATOR_OUT_DIR/TransformParameters.0.txt (*)
# OPERATOR_OUT_DIR/TransformParameters.1.txt (*)
# OPERATOR_OUT_DIR/elastix.log
ENV OPERATOR_OUT_DIR registration

# (*) Files are required in the next step (m2olie workbench)

# ?? Required ??
# RUN mkdir -p OPERATOR_OUT_DIR

COPY files/* /kaapana/app/
RUN chmod +x /kaapana/app/elastix-registration.sh
CMD ["/bin/bash", "/kaapana/app/elastix-registration.sh"]

# to test the container without using kaapana 
# docker run --rm -ti 
# -v /home/test/used/experiment_01:/data \
# -e OPERATOR_IN_DIR_FIXED=/data/fixed-input \
# -e OPERATOR_IN_DIR_MOVING=/data/moving-input \
# -e OPERATOR_OUT_DIR=/data/registration \
# <This Container>