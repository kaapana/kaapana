#!/bin/bash

../build-scripts/start_build.py
../build/kaapana-admin-chart/deploy_platform.sh --quiet --undeploy --no-hooks

sudo rm -rf /home/kaapana

../build/kaapana-admin-chart/deploy_platform.sh --quiet