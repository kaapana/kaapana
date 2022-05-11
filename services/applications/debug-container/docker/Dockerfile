FROM local-only/base-python-cpu:0.1.0

LABEL IMAGE="debug-container"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
    apt-transport-https \
    nmap \
    netcat \
    iputils-ping \
    dnsutils \
&& rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY files/requirements.txt /usr/src/app/
# RUN python3 -m pip install pip --upgrade && python3 -m pip install --no-cache-dir wheel
RUN pip3 install --no-cache-dir -r requirements.txt


COPY files/flask_headers.py /usr/src/app/
CMD ["python3","-u","flask_headers.py"]
