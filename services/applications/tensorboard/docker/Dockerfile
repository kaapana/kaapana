FROM local-only/base-python-cpu:0.1.0

LABEL IMAGE="tensorboard"
LABEL VERSION="2.8.0"
LABEL CI_IGNORE="False"

ENV INGRESS_PATH /tensorboard
ENV LOG_DIR=/data

COPY files/requirements.txt /src/requirements.txt
RUN pip3 install --no-cache-dir -r /src/requirements.txt

COPY files/tensorboard.sh /

CMD ["/bin/sh", "/tensorboard.sh"]