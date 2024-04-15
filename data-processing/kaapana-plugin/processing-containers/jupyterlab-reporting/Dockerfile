FROM local-only/base-python-cpu:latest
LABEL IMAGE="jupyterlab-reporting"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

USER 0 
COPY files/ /files
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic

RUN python -m pip install --upgrade setuptools pip && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /files/requirements.txt

CMD ["/bin/bash","/files/generate_report.sh"]