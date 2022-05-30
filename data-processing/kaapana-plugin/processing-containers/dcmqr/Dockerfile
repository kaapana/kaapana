FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="dcmqr"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt
COPY files/query.py /kaapanasrc/
COPY files/run-query.sh /kaapanasrc/

CMD /kaapanasrc/run-query.sh