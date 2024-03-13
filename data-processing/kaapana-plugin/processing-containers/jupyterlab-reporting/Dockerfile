FROM local-only/base-python-cpu:latest
LABEL IMAGE="jupyterlab-reporting"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

USER 0 
COPY files/ /files
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --upgrade setuptools pip && pip3 install -r /files/requirements.txt

CMD ["/bin/bash","/files/generate_report.sh"]