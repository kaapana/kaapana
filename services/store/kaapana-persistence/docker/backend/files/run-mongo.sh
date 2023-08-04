#!/bin/bash
docker run --rm -p 27017:27017 --name some-mongo mongo
# docker run -d --name some-mongo \
# 	-e MONGO_INITDB_ROOT_USERNAME=mongoadmin \
# 	-e MONGO_INITDB_ROOT_PASSWORD=secret \
# 	mongo
