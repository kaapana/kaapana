#!/bin/bash
set -e
helm dep update files
set +e
echo "kaapana-collections -> pre_build.sh done"
