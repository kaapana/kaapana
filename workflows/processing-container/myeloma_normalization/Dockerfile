FROM python:3.9.5-buster

LABEL IMAGE="myeloma_normalization"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

RUN python3 --version
RUN pip3 install medpy==0.4.0
RUN pip3 install SimpleITK

COPY files/norm_z_score.py .
COPY files/norm_tissue_based.py .

COPY files/convert.sh .
RUN chmod +x convert.sh

ENTRYPOINT ["/bin/bash", "./convert.sh"]
