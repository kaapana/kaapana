FROM local-only/base-python-cpu:latest

LABEL IMAGE="tensorboard"
LABEL VERSION="2.12.0"
LABEL BUILD_IGNORE="False"

ENV INGRESS_PATH /tensorboard
ENV LOG_DIR=/kaapana/mounted/tb-logs

COPY files/requirements.txt /src/requirements.txt
RUN pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /src/requirements.txt

COPY files/tensorboard.sh /

CMD ["/bin/sh", "/tensorboard.sh"]

USER 1000