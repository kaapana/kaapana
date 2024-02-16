FROM local-only/base-python-cpu:latest
LABEL IMAGE="jupyterlab-reporting"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

USER 0 
COPY files/ /files
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.1/build-scripts/constraints-0.2.1.txt --upgrade setuptools pip && pip3 install -r /files/requirements.txt

CMD ["/bin/bash","/files/generate_report.sh"]
