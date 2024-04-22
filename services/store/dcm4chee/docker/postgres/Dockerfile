FROM local-only/base-python-cpu:latest as postgres

WORKDIR /dcm4chee

RUN git clone https://github.com/dcm4che-dockerfiles/postgres-dcm4chee.git . \
    && git checkout d0c78f5d16b047b7a8a6053deec17d86254af108


FROM local-only/postgres-base:latest

LABEL IMAGE="dcm4che-postgres"
LABEL VERSION="15.6"
LABEL CI_IGNORE="False"

COPY --from=postgres /dcm4chee/docker-entrypoint-initdb.d docker-entrypoint-initdb.d/
COPY --from=postgres /dcm4chee/sql sql/
COPY --from=postgres /dcm4chee/bin /usr/bin/