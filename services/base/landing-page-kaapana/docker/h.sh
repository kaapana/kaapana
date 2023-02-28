#!/bin/bash
cd /home/ubuntu/kaapana/services/utils/base-landing-page/
docker build -t local-only/base-landing-page:latest .
cd /home/ubuntu/kaapana/services/base/landing-page-kaapana/docker/
sudo docker build -t registry.hzdr.de/kaapana/tfdamv3_ems_integration/landing-page-kaapana:0.1.3-155-g8c1b7179 .
sudo docker push registry.hzdr.de/kaapana/tfdamv3_ems_integration/landing-page-kaapana:0.1.3-155-g8c1b7179
microk8s.kubectl get pods -n base --no-headers=true | awk '/landingpage*/{print $1}' | xargs microk8s.kubectl delete -n base pod