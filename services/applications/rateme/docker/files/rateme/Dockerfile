FROM python:3.9-alpine3.12                              # small-sized alpine base image

LABEL IMAGE="rateme-app"                                # define utilization of image
LABEL VERSION="0.1.0"                                   # define specific version of image
LABEL CI_IGNORE="True"

COPY . /src/                                            # copy requirements and scripts

RUN pip3 install —upgrade pip                           # first upgrade pip
    && pip3 install -r /src/requirements.txt            # install requirements

CMD ["python3","-u","/rateme.py"]                       # execute script