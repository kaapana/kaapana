FROM dktk-jip-registry.dkfz.de/kaapana-public/multiorgansegmentation:v0.9

LABEL IMAGE="shape-organseg"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY organ_segmentation.sh /kaapana/app/organ_segmentation.sh

ENTRYPOINT ["/bin/bash", "/kaapana/app/organ_segmentation.sh"]
