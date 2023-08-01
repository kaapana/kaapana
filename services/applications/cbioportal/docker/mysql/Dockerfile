FROM docker.io/mysql:5.7

LABEL IMAGE="mysql-5.7"
LABEL VERSION="5.7"
LABEL CI_IGNORE="False"

RUN curl -o /docker-entrypoint-initdb.d/cgds.sql "https://raw.githubusercontent.com/cBioPortal/cbioportal/v5.3.6/db-scripts/src/main/resources/cgds.sql" && curl -o /docker-entrypoint-initdb.d/seed.sql.gz "https://github.com/cBioPortal/datahub/raw/master/seedDB/seedDB_hg19_archive/seed-cbioportal_hg19_v2.12.14.sql.gz"

RUN ls /docker-entrypoint-initdb.d/