#!/bin/bash

sudo docker build -t local-only/base-landing-page:0.1.1 .
cd ../../base/landing-page-kaapana/docker/
sudo docker build -t registry.hzdr.de/santhosh.parampottupadam/tfdamvp1/landing-page-kaapana:0.1.3 .
sudo docker push registry.hzdr.de/santhosh.parampottupadam/tfdamvp1/landing-page-kaapana:0.1.3
microk8s kubectl delete pods -l app-name=landingpage -n base