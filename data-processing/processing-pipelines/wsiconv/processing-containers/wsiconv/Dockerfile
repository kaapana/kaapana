FROM local-only/base-python-gpu:latest
LABEL IMAGE="wsiconv"
LABEL VERSION="1.0.0"
LABEL BUILD_IGNORE="False"


RUN mkdir /data #new
RUN mkdir /output #new
COPY files/convert.py /home
WORKDIR /home


RUN apt-get update
RUN apt-get install -y python3-pip
RUN apt-get install -y openslide-tools
RUN apt-get install -y libturbojpeg
RUN apt-get install -y nano

RUN pip3 install pydicom
RUN pip3 install wsidicomizer
RUN pip3 install wsidicomizer[openslide]
RUN pip3 install wsidicomizer[bioformats]

ENTRYPOINT ["python3", "convert.py"]
