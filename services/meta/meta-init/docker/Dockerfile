FROM local-only/base-python-cpu:latest

LABEL IMAGE="init-meta"
LABEL VERSION="2.2.0"
LABEL BUILD_IGNORE="False"

WORKDIR /
RUN mkdir /dashboards

COPY files/requirements.txt ./
RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r requirements.txt

COPY files/start.py /start.py
COPY files/saved_objects /

CMD [ "python","-u", "/start.py"]
