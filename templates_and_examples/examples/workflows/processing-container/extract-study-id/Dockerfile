FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="example-extract-study-id"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

COPY files/extract_study_id.py /

CMD ["python3","-u","/extract_study_id.py"]