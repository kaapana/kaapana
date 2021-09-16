FROM python:3.9-slim
# FROM python:3.9-alpine3.12

LABEL IMAGE="dcmstruct2nifti"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /
# RUN apk update && apk add --no-cache python3-dev gcc libc-dev  jpeg-dev zlib-dev && pip3 install --upgrade pip

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/start.py /
CMD ["python3","-u","/start.py"]
