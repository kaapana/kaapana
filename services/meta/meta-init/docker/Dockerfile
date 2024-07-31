FROM local-only/base-python-cpu:latest

LABEL IMAGE="init-meta"
LABEL VERSION="2.2.0"
LABEL BUILD_IGNORE="False"

WORKDIR /
RUN mkdir /dashboards

COPY files/requirements.txt ./
RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r requirements.txt

#COPY files/init_meta.py /init_meta.py

COPY files/start.py /start.py
COPY files/saved_objects /

COPY files/start.sh /start.sh

#CMD ["/bin/bash", "/start.sh"]
CMD [ "python","-u", "/start.py"]
