FROM dktk-jip-registry.dkfz.de/jip/multiorgansegmentation:v0.9

LABEL IMAGE="organseg"
LABEL VERSION="1.1-vdev"
LABEL CI_IGNORE="False"

WORKDIR /
RUN apt install nano

COPY organ_segmentation.sh /organ_segmentation.sh

ENTRYPOINT ["/bin/bash", "/organ_segmentation.sh"]


