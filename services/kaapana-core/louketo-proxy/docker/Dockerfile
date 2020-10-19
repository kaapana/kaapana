FROM golang:1.14.4 AS build-env

LABEL IMAGE="louketo-proxy"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /opt

RUN git clone https://github.com/louketo/louketo-proxy.git 
WORKDIR /opt/louketo-proxy
RUN git checkout aa9ae98d6414045628d17b5c43a3f17cdb7f799b

RUN make

FROM registry.access.redhat.com/ubi8/ubi-minimal:8.2

WORKDIR "/opt/louketo"
RUN echo "louketo:x:1000:louketo" >> /etc/group && \
    echo "louketo:x:1000:1000:louketo user:/opt/louketo:/sbin/nologin" >> /etc/passwd && \
    chown -R louketo:louketo /opt/louketo && \
    chmod -R g+rw /opt/louketo

COPY --from=build-env /opt/louketo-proxy/templates ./templates
COPY --from=build-env /opt/louketo-proxy/bin/louketo-proxy ./

RUN chmod +x louketo-proxy

USER 1000
ENTRYPOINT [ "/opt/louketo/louketo-proxy" ]
