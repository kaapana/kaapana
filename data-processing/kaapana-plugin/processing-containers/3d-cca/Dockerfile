FROM local-only/base-python-cpu:latest

LABEL IMAGE="cca"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /
RUN pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
