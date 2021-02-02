FROM python:3.9-alpine3.12

LABEL IMAGE="zip-unzip"
LABEL VERSION="3.0.0"
LABEL CI_IGNORE="False"

# RUN apk --no-cache add zip
RUN mkdir -p /src
COPY files/ /src/

CMD ["python3","-u","src/process.py"]
