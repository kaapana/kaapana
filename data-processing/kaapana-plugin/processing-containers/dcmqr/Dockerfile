FROM local-only/base-python-cpu:latest

LABEL IMAGE="dcmqr"
LABEL VERSION="0.1.1"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip3 install -c /constraints.txt --no-cache-dir -r /requirements.txt
COPY files/query.py /kaapana/app/
COPY files/run-query.sh /kaapana/app/

CMD /kaapana/app/run-query.sh