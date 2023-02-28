FROM httpd:2.4.55

LABEL IMAGE="openedc"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.system /kaapana/app/
RUN apt-get update -y && cat /kaapana/app/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/imi-muenster/OpenEDC /usr/local/apache2/htdocs/openedc && \
    cd /usr/local/apache2/htdocs/openedc && \
    git checkout ca70577daa7b7bc34d3d586e564c7222636bddd7

