FROM dktk-jip-registry.dkfz.de/dcipher-core/screenradiomic:develop

LABEL IMAGE="mitk-radiomics"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /
ADD files/radiomics.py /radiomics.py
ADD radiomics.sh /

ENTRYPOINT ["/bin/bash", "/radiomics.sh"]
