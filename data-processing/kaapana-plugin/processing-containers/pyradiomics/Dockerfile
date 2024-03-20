FROM local-only/base-python-cpu:latest

LABEL IMAGE="pyradiomics"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

#current pip pyradiomics==3.1.0 is not working with python3.10, install from git:
RUN apt-get update && apt-get install -y python-dev-is-python3
RUN git clone https://github.com/AIM-Harvard/pyradiomics.git pyradiomics \
    && cd pyradiomics \
    && python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r requirements.txt \
    && python setup.py install


COPY files/requirements.txt /kaapana/app/
RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt && rm /kaapana/app/requirements.txt 

COPY files/pyradiomics.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/pyradiomics.py"]