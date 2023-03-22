FROM local-only/base-python-cpu:latest

LABEL IMAGE="mask2nifti"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/develop/build-scripts/constraints-0.1.3.txt --no-cache-dir -r /kaapana/app/requirements.txt

#Release 1.2.5
RUN mkdir -p /kaapana/app/src && wget --no-check-certificate https://github.com/QIICR/dcmqi/releases/download/v1.2.5/dcmqi-1.2.5-linux.tar.gz -O /kaapana/app/src/dcmqi.tar.gz \
    && mkdir -p /kaapana/app/dcmqi && tar -xzf /kaapana/app/src/dcmqi.tar.gz --strip 1 -C /kaapana/app/dcmqi && rm -rf /kaapana/app/src/dcmqi.tar.gz

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
