#!/bin/bash
set -eu -o pipefail

./init-security.sh &
./opensearch-docker-entrypoint.sh opensearch 
