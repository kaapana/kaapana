FROM local-only/base-python-cpu:latest

LABEL IMAGE="dcmqr"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt
COPY files/query.py /app/
COPY files/run-query.sh /app/

CMD /app/run-query.sh