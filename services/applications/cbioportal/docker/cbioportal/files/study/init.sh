#!/usr/bin/env bash
# download data hub study and import

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

DATAHUB_STUDIES="${DATAHUB_STUDIES:-lgg_ucsf_2014}"
for study in ${DATAHUB_STUDIES}; do
        wget -O ${study}.tar.gz "https://cbioportal-datahub.s3.amazonaws.com/${study}.tar.gz"
        tar xvfz ${study}.tar.gz
done
