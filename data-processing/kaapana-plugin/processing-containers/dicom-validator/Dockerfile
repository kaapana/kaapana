FROM local-only/base-python-cpu:latest

LABEL IMAGE="dicom-validator"
LABEL VERSION="v1.2.4"
LABEL BUILD_IGNORE="False"

RUN apt-get -y update && apt-get install -y xutils-dev

# install dicom3tools for dciodvfy
# http://www.dclunie.com/dicom3tools
ARG snapshottarget=dicom3tools_1.00.snapshot.20240227102104.tar.bz2
ARG snapshotdir=/dicom3tools_snapshot
# Start installing
RUN wget http://www.dclunie.com/dicom3tools/workinprogress/${snapshottarget} \
  && mkdir ${snapshotdir} \
  && tar xvjf ${snapshottarget} -C ${snapshotdir} --strip-components=1 \
  && rm ${snapshottarget}
WORKDIR ${snapshotdir}
RUN ./Configure \
  && imake -I./config \
  && make World \
  && make install \
  && make clean \
  && rm -r ${snapshotdir}

# reset work directory
WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt -r /kaapana/app/requirements.txt


COPY files/* /kaapana/app/

# Trigger the download of dicom revision of given tag, e.g. `2024a`
# stores the revision as JSON in `/kaapana/dicom-revisions/` inside the container
RUN python3 -u base.py download_revision 2024a

CMD ["python3","-u", "/kaapana/app/start.py"]