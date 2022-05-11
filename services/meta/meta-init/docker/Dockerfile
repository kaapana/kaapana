FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="init-meta"
LABEL VERSION="6.8.12"
LABEL CI_IGNORE="False"

WORKDIR /
RUN mkdir /dashboards

COPY files/init_meta.py /init_meta.py

CMD [ "python","-u", "/init_meta.py" ]
