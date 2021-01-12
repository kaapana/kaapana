# needed 18.04 for dcmtk=3.6.2-3build3
FROM ubuntu:18.04 

LABEL IMAGE="bin2dcm"
LABEL VERSION="3.6.2-vdev"
LABEL CI_IGNORE="False"

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    dcmtk=3.6.2-3build3 \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/template.xml .
COPY files/start.py .

CMD ["python3","-u","/start.py"]
