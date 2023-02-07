FROM local-only/base-python-cpu:latest

LABEL IMAGE="dcmqi"
LABEL VERSION="v1.2.4"
LABEL CI_IGNORE="False"

# set work directory
WORKDIR /app

COPY files/requirements.txt /app
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

#Release 1.2.5
RUN mkdir -p /app/src && wget --no-check-certificate https://github.com/QIICR/dcmqi/releases/download/v1.2.5/dcmqi-1.2.5-linux.tar.gz -O /app/src/dcmqi.tar.gz \
    && mkdir -p /app/dcmqi && tar -xzf /app/src/dcmqi.tar.gz --strip 1 -C /app/dcmqi && rm -rf /app/src/dcmqi.tar.gz

COPY files/* /app/
RUN chmod +x /app/convert.sh

ENTRYPOINT ["/bin/bash", "/app/convert.sh"]