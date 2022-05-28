FROM ubuntu:20.04

LABEL IMAGE="debug_container"
LABEL VERSION="1.0"
LABEL CI_IGNORE="False"

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    apt-transport-https \
    git \
    curl \
    nmap \
    netcat \
    nano \
    iputils-ping \
    dnsutils \
&& rm -rf /var/lib/apt/lists/*



RUN curl -k -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - 
RUN echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update && apt-get install -y kubectl && rm -rf /var/lib/apt/lists/*


# update pip
RUN python3 -m pip install pip --upgrade && python3 -m pip install --no-cache-dir wheel

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY files/requirements.txt /usr/src/app/
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/flask_headers.py /usr/src/app/

# Expose the Flask port
EXPOSE 5000


CMD ["python3","-u","flask_headers.py"]
