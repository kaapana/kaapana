FROM local-only/base-python-cpu:latest

LABEL IMAGE="otsus-method"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    pandoc

RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/ /kaapana/app/
CMD ["python3","-u","/kaapana/app/otsus_method.py"]