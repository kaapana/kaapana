FROM local-only/base-python-cpu:latest

LABEL IMAGE="init-meta"
LABEL VERSION="2.2.0"
LABEL CI_IGNORE="False"

WORKDIR /
RUN mkdir /dashboards

COPY files/requirements.txt ./
RUN pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt --no-cache-dir -r requirements.txt

COPY files/init_meta.py /init_meta.py

CMD [ "python","-u", "/init_meta.py" ]
