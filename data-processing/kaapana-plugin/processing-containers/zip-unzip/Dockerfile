FROM local-only/base-python-alpine:latest

LABEL IMAGE="zip-unzip"
LABEL VERSION="3.0.0"
LABEL CI_IGNORE="False"

# RUN apk --no-cache add zip
# RUN mkdir -p /kaapanasrc
COPY files/ /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/process.py"]
