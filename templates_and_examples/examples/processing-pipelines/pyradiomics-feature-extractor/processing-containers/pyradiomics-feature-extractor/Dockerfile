# use base python CPU image since pyradiomics doesn't utilize GPU
FROM local-registry.services.svc.cluster.local:5000/base-python-cpu:latest

# name and version of the processing container image
LABEL IMAGE="pyradiomics-extract-features"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

# set working dir inside container
WORKDIR /kaapana/app

# copy files into the container
COPY files/* /kaapana/app

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

# install from git:
RUN apt-get update && apt-get install -y python-dev-is-python3 \
    && git clone -b "v3.1.0" --single-branch https://github.com/AIM-Harvard/pyradiomics.git pyradiomics \
    && cd pyradiomics \
    # && git checkout v3.1.0 \
    && python3.10 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt -r requirements.txt \
    && python3.10 setup.py install

# run the script
CMD ["python3", "-u", "extract_features.py"]
