FROM dktk-jip-registry.dkfz.de/kaapana-public/multiorgansegmentation:v0.9

LABEL IMAGE="shape-organseg"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /app

COPY organ_segmentation.sh /app/organ_segmentation.sh

ENTRYPOINT ["/bin/bash", "/app/organ_segmentation.sh"]
