FROM registry.hzdr.de/kaapana/public/multiorgansegmentation:v0.9

LABEL IMAGE="shape-organseg"
LABEL VERSION="0.1.1"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY organ_segmentation.sh /kaapana/app/organ_segmentation.sh

ENTRYPOINT ["/bin/bash", "/kaapana/app/organ_segmentation.sh"]
