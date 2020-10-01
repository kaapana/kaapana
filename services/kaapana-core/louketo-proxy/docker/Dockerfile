FROM golang AS build-env

LABEL IMAGE="louketo-proxy"
LABEL VERSION="0.1.0-vdev"
LABEL CI_IGNORE="False"

WORKDIR /opt

RUN git clone https://github.com/louketo/louketo-proxy.git 
WORKDIR /opt/louketo-proxy
RUN git checkout b043dea3a21d9ca5955edbe194b572db9b7d6b8c

RUN make
RUN make release

FROM golang

WORKDIR /app
COPY --from=build-env /opt/louketo-proxy/bin/louketo-proxy /app/louketo-proxy
CMD /app/louketo-proxy
