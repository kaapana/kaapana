FROM local-only/base-python-alpine:latest

LABEL IMAGE="dcm-extractor"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dcm_extractor.py /kaapanasrc/

CMD ["python3", "-u", "/kaapanasrc/dcm_extractor.py"]