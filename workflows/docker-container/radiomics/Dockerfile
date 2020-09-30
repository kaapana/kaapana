FROM dktk-jip-registry.dkfz.de/dcipher-core/screenradiomic:develop

LABEL IMAGE="radiomics"
LABEL VERSION="1.0.1-vdev"
LABEL CI_IGNORE="False"

WORKDIR /
ADD files/radiomics.py /radiomics.py
ADD radiomics.sh /

ENTRYPOINT ["/bin/bash", "/radiomics.sh"]
