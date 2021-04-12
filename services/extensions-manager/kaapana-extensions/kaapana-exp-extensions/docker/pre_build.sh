#!/bin/bash
set -e
helm dep update files
set +e
echo "kaapana-extensions -> pre_build.sh done"
