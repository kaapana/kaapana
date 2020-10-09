FROM python:3.9-alpine3.12

LABEL IMAGE="dcmqi"
LABEL VERSION="1.3-vdev"
LABEL CI_IGNORE="False"


# set work directory
WORKDIR /dcmqi

RUN apt-get update && apt-get install nano
RUN pip install pandas

#Release 1.0.4
RUN curl -L -O https://github.com/QIICR/dcmqi/releases/download/v1.2.2/dcmqi-1.2.2-linux.tar.gz
RUN tar xzvf dcmqi-1.2.2-linux.tar.gz

#COPY files/create_segmentation_json.py .
COPY files/code_lookup_table.csv .
COPY files/itkimage2segimage.py .
COPY files/segimage2itkimage.py .
COPY files/tid1500writer.py .
COPY files/convert.sh .
RUN chmod +x convert.sh

ENTRYPOINT ["/bin/bash", "./convert.sh"]