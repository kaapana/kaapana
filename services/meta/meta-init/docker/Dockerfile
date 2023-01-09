FROM python:3.9-alpine3.12

LABEL IMAGE="init-meta"
LABEL VERSION="2.2.0"
LABEL CI_IGNORE="False"

WORKDIR /
RUN mkdir /dashboards

COPY files/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY files/init_meta.py /init_meta.py

CMD [ "python","-u", "/init_meta.py" ]
