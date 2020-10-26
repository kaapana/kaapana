FROM python:3.9-alpine3.12

LABEL IMAGE="example-pool-jsons"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

COPY files/pool_jsons.py /

CMD ["python3","-u","/pool_jsons.py"]