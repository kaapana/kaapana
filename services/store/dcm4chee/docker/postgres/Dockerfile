FROM local-only/base-python-cpu:latest as postgres

WORKDIR /dcm4chee

RUN git clone https://github.com/dcm4che-dockerfiles/postgres-dcm4chee.git . \
    && git checkout 0633903ae932158987b3328f84284c73cba91a58


FROM local-only/postgres-base:latest

LABEL IMAGE="dcm4che-postgres"
LABEL VERSION="17.1"
LABEL BUILD_IGNORE="False"

COPY --from=postgres /dcm4chee/docker-entrypoint-initdb.d docker-entrypoint-initdb.d/
COPY --from=postgres /dcm4chee/sql sql/
COPY --from=postgres /dcm4chee/bin /usr/bin/
