#!/bin/bash
docker build -t dev-osd .
id=$(docker create dev-osd)
docker cp $id:/home/node/OpenSearch-Dashboards/plugins/workflow-trigger/build/workflowTrigger-2.2.0.zip os-dashboards/docker/files
docker rm -v $id