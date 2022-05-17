#!/bin/bash
echo '**********************************************************************'
echo 'Please  ensure that installation.sh & fetstesting.sh script has executable permission'
echo '**********************************************************************'

sudo apt update && sudo apt install -y curl git python3 python3-pip
git clone https://github.com/mlcommons/medperf.git
cd medperf && cd cli
git pull origin cli-assoc-comp-test
pip3 install -e .


cd ..
wget https://storage.googleapis.com/medperf-storage/brats-medperf-environment.tar.gz 

mkdir medperf-env
mv brats-medperf-environment.tar.gz medperf-env/
cd medperf-env/
tar -xvf brats-medperf-environment.tar.gz

rm brats-medperf-environment.tar.gz

docker pull mlcommons/fets_metrics

docker pull mlcommons/fets_data-prep

echo '**********************************************************************'
echo 'Please reboot your system and then run the fetstesting.sh script'
echo '**********************************************************************'
