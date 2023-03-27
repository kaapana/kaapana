#!/bin/bash
cd /home/ubuntu/kaapana/services/utils/base-landing-page/
docker build --build-arg "http_proxy=http://www-int2.dkfz-heidelberg.de:80" --build-arg "https_proxy=http://www-int2.dkfz-heidelberg.de:80" -t local-only/base-landing-page:latest .
cd /home/ubuntu/kaapana/services/base/landing-page-kaapana/docker/
docker build -t registry.hzdr.de/kaushal.parekh/tfdamvp3-20230228/landing-page-kaapana:0.1.3-614-gc1651cab .
docker push registry.hzdr.de/kaushal.parekh/tfdamvp3-20230228/landing-page-kaapana:0.1.3-614-gc1651cab
microk8s.kubectl get pods -n base --no-headers=true | awk '/landingpage*/{print $1}' | xargs microk8s.kubectl delete -n base pod