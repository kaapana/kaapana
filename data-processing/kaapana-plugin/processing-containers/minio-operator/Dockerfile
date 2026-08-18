FROM local-only/base-python-cpu:latest

LABEL IMAGE="minio-operator"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /

COPY files/requirements.txt /kaapana/app/
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN python -m pip install -c /constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/start.py /kaapana/app/

CMD ["python","-u","/kaapana/app/start.py"]