FROM local-only/base-python-cpu:latest

LABEL IMAGE="pyradiomics"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libnss3-dev \
    libsqlite3-dev \
    libreadline-dev \
    libffi-dev \
    curl \
    libbz2-dev \
    liblzma-dev \
    libgdbm-dev

RUN wget https://www.python.org/ftp/python/3.10.15/Python-3.10.15.tgz \
    && tar -xzf Python-3.10.15.tgz \
    && cd Python-3.10.15 \
    && ./configure --enable-optimizations \
    && make -j$(nproc) \
    && make altinstall \
    && cd .. \
    && rm -rf Python-3.10.15 Python-3.10.15.tgz

RUN ln -sf /usr/local/bin/python3.10 /usr/local/bin/python3
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python3.10 get-pip.py \
    && rm get-pip.py


#current pip pyradiomics==3.1.0 is not working with python3.10, install from git:
RUN apt-get update && apt-get install -y python-dev-is-python3 \
    && git clone https://github.com/AIM-Harvard/pyradiomics.git pyradiomics \
    && cd pyradiomics \
    # && git checkout v3.1.0 \
    && python3.10 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r requirements.txt \
    && python3.10 setup.py install


COPY files/requirements.txt /kaapana/app/
RUN python3.10 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt && rm /kaapana/app/requirements.txt 

COPY files/pyradiomics.py /kaapana/app/

CMD ["python3.10","-u","/kaapana/app/pyradiomics.py"]