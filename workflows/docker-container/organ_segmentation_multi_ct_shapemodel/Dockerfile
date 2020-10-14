FROM dktk-jip-registry.dkfz.de/jip/multiorgansegmentation:v0.9

LABEL IMAGE="shape-organseg"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /
RUN apt install nano

COPY organ_segmentation.sh /organ_segmentation.sh

ENTRYPOINT ["/bin/bash", "/organ_segmentation.sh"]


