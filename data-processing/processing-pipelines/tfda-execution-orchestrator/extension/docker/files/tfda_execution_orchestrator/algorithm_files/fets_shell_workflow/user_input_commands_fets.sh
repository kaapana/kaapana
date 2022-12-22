#!/bin/bash
echo "Container evaluation for the Federated Tumoor Segmentation Challenge 2022 - Task 2"

echo "Copy algorithm files to another location"
[ -f "/home/ubuntu/algorithm_files/*" ] && cp "/home/ubuntu/algorithm_files/*" /home/ubuntu/tarball/

echo "Update submission tarfile name in MLCube config"
sed -i -E 's@/home/ubuntu/tarball/@/home/ubuntu/tarball/submission.tar' /home/ubuntu/tarball/mlcube.yaml

echo "Run Mini conda Installation for Cuda Support"
source /home/ubuntu/Miniconda3-py38_4.12.0-Linux-x86_64.sh -b -p /home/ubuntu/miniconda3

echo "Convert docker to singularity using MLCube"
mlcube configure --platform=singularity --mlcube=/home/ubuntu/tarball/mlcube.yaml

echo "Run MedPerf client on the submission"
medperf --no-cleanup --storage=/home/ubuntu/medperf-env --platform=singularity --log=debug --infer-timeout=600 test -b 1 -m /home/ubuntu/tarball

echo "Copy MedPerf logs and results into /home/ubuntu/results folder"
[ -f "/home/ubuntu/medperf-env/logs/medperf.log" ] && cp "/home/ubuntu/medperf-env/logs/medperf.log" /home/ubuntu/medperf-env/results/
[ -f "/home/ubuntu/medperf-env/results/*" ] && cp -r "/home/ubuntu/medperf-env/results" /home/ubuntu/results/
