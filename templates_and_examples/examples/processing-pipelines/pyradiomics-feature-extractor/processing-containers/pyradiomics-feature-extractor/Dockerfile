# use base python CPU image since pyradiomics doesn't utilize GPU
FROM local-only/base-python-cpu:latest

# name and version of the processing container image
LABEL IMAGE="pyradiomics-extract-features"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

# set working dir inside container
WORKDIR /kaapana/app

# copy files into the container
COPY files/* /kaapana/app

# install required python packages
# current pip pyradiomics==3.1.0 is not working with python3.11, install from source
RUN apt-get update && apt-get install -y python-dev-is-python3
RUN git clone https://github.com/AIM-Harvard/pyradiomics.git pyradiomics \
    && cd pyradiomics \
    && python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r requirements.txt \
    && python setup.py install

# run the script
CMD ["python3", "extract_features.py"]
