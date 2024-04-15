FROM local-only/base-python-cpu:latest

LABEL IMAGE="dcmqr"
LABEL VERSION="0.1.1"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /
RUN pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /requirements.txt
COPY files/query.py /kaapana/app/
COPY files/run-query.sh /kaapana/app/

CMD /kaapana/app/run-query.sh