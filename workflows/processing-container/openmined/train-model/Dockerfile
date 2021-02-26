FROM continuumio/miniconda3

LABEL IMAGE="openmined-provide-data"
LABEL VERSION="0.1.0-vdev"
LABEL CI_IGNORE="True"

# Setup workspace environment
RUN apt-get update && apt-get install -y gcc

# pysyft v0.2.9
RUN python -m pip install git+https://github.com/OpenMined/PySyft.git@3852ca9e78d5163b52776b231f469e32e6c8be01

RUN mkdir /utils
COPY files/dataset.py files/models.py ./utils/

COPY files/process.py ./

#CMD tail -f  /dev/null
CMD ["python3","-u","/process.py"]