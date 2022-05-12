FROM python:3.9-alpine3.12

LABEL IMAGE="init-meta"
LABEL VERSION="6.8.12"
LABEL CI_IGNORE="False"

WORKDIR /
RUN mkdir /dashboards

COPY files/init_meta.py /init_meta.py
COPY files/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python","-u", "/init_meta.py" ]
