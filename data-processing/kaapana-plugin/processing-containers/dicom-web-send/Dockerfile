FROM local-only/base-python-cpu:latest

LABEL IMAGE="dicomwebsend"
LABEL VERSION="0.50.0"
LABEL BUILD_IGNORE="False"

# RUN apk add build-base python-dev py-pip jpeg-dev zlib-dev
# ENV LIBRARY_PATH=/lib:/usr/lib

WORKDIR /
RUN pip3 install --upgrade pip

COPY files/requirements.txt /
RUN pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r requirements.txt

COPY files/dcmweb.py /kaapana/app/


CMD ["python","-u","/kaapana/app/dcmweb.py"]

