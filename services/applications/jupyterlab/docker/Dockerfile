FROM local-only/base-python-gpu:latest

LABEL IMAGE="jupyterlab"
LABEL VERSION="3.3.2"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /app/
RUN python -m pip install --upgrade setuptools pip && pip3 install --force-reinstall -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt -r /app/requirements.txt

RUN jupyter-lab --generate-config && \
    mkdir -m 777 -p /kaapana/app/.jupyter/ && \
    cp /root/.jupyter/jupyter_lab_config.py /kaapana/app/.jupyter/

COPY files/start.sh /app/

RUN mkdir -p /kaapana/app && \
    chown -R 1000:1000 /kaapana && \
    chmod -R 755 /kaapana/app

ENV HOME="/kaapana"
ENV INGRESS_PATH="jupyter-lab"
ENV SHELL="/bin/bash"

# fix for "I have no name!" issue
RUN echo "kaapana:x:1000:1000::/kaapana:/bin/bash" >> /etc/passwd

USER 1000

CMD ["/bin/bash", "/app/start.sh"]