#!/bin/bash
set -e

DOCSPATH="$( cd "$(dirname "$0")" ; pwd -P )"
echo "DOCSPATH:" $DOCSPATH

if python -c "import sphinx" &> /dev/null; then
    echo 'Python requirements already present...'
else
    echo 'Install python requirements...'
    python3 -m pip install -r $DOCSPATH/requirements.txt
fi

set +e
make -C $DOCSPATH clean
set -e
make -C $DOCSPATH html && echo MAKE DOCS OK || (echo MAKE DOCS Failed && exit 1)
echo "Documentation -> pre_build.sh done"
