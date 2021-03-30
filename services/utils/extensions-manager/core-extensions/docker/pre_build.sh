#!/bin/bash
# set -e
#TODO add proper error handling!
helm dep update files
# set +e
echo "core-extensions -> pre_build.sh done"
