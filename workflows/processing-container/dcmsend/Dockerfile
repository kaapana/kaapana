FROM ubuntu:20.04

LABEL IMAGE="dcmsend"
LABEL VERSION="3.6.2"
LABEL CI_IGNORE="False"

ENV TZ=Europe/Kiev
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -y && apt-get install -y \
    dcmtk \
    python3-pip \
    && apt-get clean

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/process.py .

CMD ["python3","-u","/process.py"]
