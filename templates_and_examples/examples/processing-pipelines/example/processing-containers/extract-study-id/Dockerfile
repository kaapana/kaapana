FROM local-only/base-python-cpu:latest

LABEL IMAGE="example-extract-study-id"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/extract_study_id.py /kaapanasrc/
WORKDIR /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/extract_study_id.py"]