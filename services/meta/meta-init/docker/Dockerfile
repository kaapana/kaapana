FROM local-only/base-python-cpu:latest

LABEL IMAGE="init-meta"
LABEL VERSION="2.2.0"
LABEL BUILD_IGNORE="False"

WORKDIR /
RUN mkdir /dashboards

COPY files/requirements.txt ./
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip install -c /constraints.txt --no-cache-dir -r requirements.txt

COPY files/start.py /start.py
COPY files/saved_objects /

CMD [ "python","-u", "/start.py"]
