FROM local-only/base-python-cpu:latest

LABEL IMAGE="dcm-extractor"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/dcm_extractor.py /app/

CMD ["python3", "-u", "/app/dcm_extractor.py"]