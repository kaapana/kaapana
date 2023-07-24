FROM docker.io/mysql:5.7

LABEL IMAGE="mysql-5.7"
LABEL VERSION="5.7"
LABEL CI_IGNORE="False"

COPY ./files/data/cgds.sql /docker-entrypoint-initdb.d/cgds.sql
COPY ./files/data/seed.sql.gz /docker-entrypoint-initdb.d/seed.sql.gz