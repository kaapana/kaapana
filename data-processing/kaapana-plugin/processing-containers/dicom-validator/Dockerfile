FROM local-only/base-python-cpu:latest

LABEL IMAGE="dicom-validator"
LABEL VERSION="v1.2.4"
LABEL BUILD_IGNORE="False"

RUN apt-get -y update && apt-get install -y \
  wget \
  unzip \
  build-essential \
  xutils-dev

# install dicom3tools for dciodvfy
# http://www.dclunie.com/dicom3tools
ARG snapshottarget=dicom3tools_1.00.snapshot.20240227102104.tar.bz2
ARG snapshotdir=/dicom3tools_snapshot
# Start installing
RUN wget http://www.dclunie.com/dicom3tools/workinprogress/${snapshottarget}
RUN mkdir ${snapshotdir}
RUN tar xvjf ${snapshottarget} -C ${snapshotdir} --strip-components=1
RUN rm ${snapshottarget}
WORKDIR ${snapshotdir}
RUN ./Configure
RUN imake -I./config
RUN make World
RUN make install
RUN make clean
RUN rm -r ${snapshotdir}

# copy the latest source revision inside the container dicom-validator directory
COPY dicom-revisions/ /kaapana/dicom-revisions/
RUN ls --recursive /kaapana/dicom-revisions

# reset work directory
WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /kaapana/app/requirements.txt


COPY files/* /kaapana/app/

CMD ["python3","-u", "/kaapana/app/start.py"]