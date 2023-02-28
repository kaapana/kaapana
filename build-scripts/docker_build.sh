#!/bin/bash

echo Cloning from $1
git clone $1
pip install -r /kaapana/app/kaapana/build-scripts/requirements.txt
cp /kaapana/app/kaapana/build-scripts/build-config-template.yaml /kaapana/app/kaapana/build-scripts/build-config.yaml
RUN  sed -i 's/container_engine: "docker"/container_engine: "podman"/g' /kaapana/app/kaapana/build-scripts/build-config.yaml
python3 /kaapana/app/kaapana/build-scripts/start_build.py ${@:2}