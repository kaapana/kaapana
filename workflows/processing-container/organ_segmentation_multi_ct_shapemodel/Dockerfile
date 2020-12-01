FROM dktk-jip-registry.dkfz.de/kaapana-public/multiorgansegmentation:v0.9

LABEL IMAGE="shape-organseg"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="True"

WORKDIR /
RUN apt install nano

COPY organ_segmentation.sh /organ_segmentation.sh

ENTRYPOINT ["/bin/bash", "/organ_segmentation.sh"]


