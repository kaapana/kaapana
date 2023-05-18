FROM local-only/base-python-cpu:latest

LABEL IMAGE="dcmqi"
LABEL VERSION="v1.2.4"
LABEL CI_IGNORE="False"

# set work directory
WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

#Release 1.2.5
RUN mkdir -p /kaapana/app/src && wget --no-check-certificate https://github.com/QIICR/dcmqi/releases/download/v1.2.5/dcmqi-1.2.5-linux.tar.gz -O /kaapana/app/src/dcmqi.tar.gz \
    && mkdir -p /kaapana/app/dcmqi && tar -xzf /kaapana/app/src/dcmqi.tar.gz --strip 1 -C /kaapana/app/dcmqi && rm -rf /kaapana/app/src/dcmqi.tar.gz

COPY files/* /kaapana/app/
RUN chmod +x /kaapana/app/convert.sh

ENTRYPOINT ["/bin/bash", "/kaapana/app/convert.sh"]