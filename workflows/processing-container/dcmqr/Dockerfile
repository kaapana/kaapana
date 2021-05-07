FROM python:3.9-alpine3.12

LABEL IMAGE="dcmqr"
LABEL VERSION="0.1.1-vdev"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt
COPY files/query.py .
COPY files/run-query.sh .

CMD ./run-query.sh