#!/bin/sh
set -x
cd "$(dirname $0)"
docker run -e COUCHDB_USER=admin -e COUCHDB_PASSWORD=asdf -p 5984:5984 -d couchdb -v "$(pwd)/data:/opt/couchdb/data"
