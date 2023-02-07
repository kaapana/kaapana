FROM local-only/base-python-cpu:latest

LABEL IMAGE="example-pool-jsons"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/pool_jsons.py /app/
WORKDIR /app/

CMD ["python3","-u","/app/pool_jsons.py"]