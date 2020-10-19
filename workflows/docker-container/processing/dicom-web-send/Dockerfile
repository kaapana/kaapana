FROM python:3.9-alpine3.12

LABEL IMAGE="dicomwebsend"
LABEL VERSION="0.50.0"
LABEL CI_IGNORE="False"

# RUN apk add build-base python-dev py-pip jpeg-dev zlib-dev
# ENV LIBRARY_PATH=/lib:/usr/lib

WORKDIR /
RUN pip3 install --upgrade pip

COPY requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

ADD dcmweb.py /


CMD ["python","-u","/dcmweb.py"]
