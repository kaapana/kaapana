FROM python:3

LABEL IMAGE="dcmqi"
LABEL VERSION="v1.2.4"
LABEL CI_IGNORE="False"

# set work directory
WORKDIR /app

COPY files/requirements.txt ./
RUN pip3 install -r ./requirements.txt

#Release 1.2.4
RUN mkdir -p /app/src && wget --no-check-certificate https://github.com/QIICR/dcmqi/releases/download/v1.2.4/dcmqi-1.2.4-linux.tar.gz -O /app/src/dcmqi.tar.gz \
    && mkdir -p /app/dcmqi && tar -xzf /app/src/dcmqi.tar.gz --strip 1 -C /app/dcmqi && rm -rf /app/src/dcmqi.tar.gz

#RUN cat /etc/os-release
RUN apt-get update
RUN apt-get -y install vim
#COPY files/create_segmentation_json.py .
COPY files/code_lookup_table.json .
COPY files/tid1500_template.json .
COPY files/itkimage2segimage.py .
COPY files/segimage2itkimage.py .
COPY files/tid1500writer.py .
COPY files/convert.sh .
RUN chmod +x convert.sh

ENTRYPOINT ["/bin/bash", "./convert.sh"]