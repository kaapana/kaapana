FROM local-only/base-python-cpu:latest

LABEL IMAGE="example-pool-jsons"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/pool_jsons.py /kaapanasrc/
WORKDIR /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/pool_jsons.py"]