FROM docker.io/httpd:2.4.56

LABEL IMAGE="openedc"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/imi-muenster/OpenEDC /usr/local/apache2/htdocs/openedc && \
    cd /usr/local/apache2/htdocs/openedc && \
    git checkout ca70577daa7b7bc34d3d586e564c7222636bddd7

