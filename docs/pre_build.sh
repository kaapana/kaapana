#!/bin/bash
set -e

DOCSPATH="$( cd "$(dirname "$0")" ; pwd -P )"
echo "DOCSPATH:" $DOCSPATH

set +e
rm -r $SCRIPTPATH/build
set -e
make -C $DOCSPATH html && echo MAKE DOCS OK || (echo MAKE DOCS Failed && exit 1)
echo "Documentation -> pre_build.sh done"