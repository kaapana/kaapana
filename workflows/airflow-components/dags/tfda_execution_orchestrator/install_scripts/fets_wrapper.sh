#!/bin/bash
sudo apt update && sudo apt install -y curl git python3 python3-pip 

git clone https://github.com/mlcommons/medperf.git 

cd medperf && cd cli 

git pull origin cli-assoc-comp-test

pip3 install -e . 

reboot may be  or source ???

cd medperf



wget https://storage.googleapis.com/medperf-storage/brats-medperf-environment.tar.gz 

mkdir medperf-env
mv brats-medperf-environment.tar.gz medperf-env/
cd medperf-env/

tar -xvf brats-medperf-environment.tar.gz

rm brats-medperf-environment.tar.gz

docker pull mlcommons/fets_metrics

docker pull mlcommons/fets_data-prep

docker pull mlcommons/fets_inference_deepmedic

cd ..

medperf --storage=./medperf-env test -b 3