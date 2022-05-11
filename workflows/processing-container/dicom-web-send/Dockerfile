FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="dicomwebsend"
LABEL VERSION="0.50.0"
LABEL CI_IGNORE="False"

# RUN apk add build-base python-dev py-pip jpeg-dev zlib-dev
# ENV LIBRARY_PATH=/lib:/usr/lib

WORKDIR /
RUN pip3 install --upgrade pip

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/dcmweb.py /kaapanasrc/


CMD ["python","-u","/kaapanasrc/dcmweb.py"]
