FROM local-only/base-python-gpu:latest

LABEL IMAGE="jupyterlab"
LABEL VERSION="3.3.2"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /app/
RUN python -m pip install --upgrade setuptools pip && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /app/requirements.txt

RUN jupyter-lab --generate-config && \
    mkdir -m 777 -p /kaapana/app/.jupyter/ && \
    cp /root/.jupyter/jupyter_lab_config.py /kaapana/app/.jupyter/

COPY files/start.sh /app/

ENV HOME "kaapana"
RUN mkdir -m 744 kaapana && chown -R 1000 kaapana
USER 1000

ENV INGRESS_PATH="jupyter-lab"

CMD ["/bin/bash", "/app/start.sh"]