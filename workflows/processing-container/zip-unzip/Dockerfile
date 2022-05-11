FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="zip-unzip"
LABEL VERSION="3.0.0"
LABEL CI_IGNORE="False"

# RUN apk --no-cache add zip
RUN mkdir -p /src
COPY files/ /src/

CMD ["python3","-u","src/process.py"]
