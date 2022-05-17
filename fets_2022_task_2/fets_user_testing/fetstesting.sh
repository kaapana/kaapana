#!/bin/bash

YOUR_DOCKER_CONTAINER='mlcommons/fets_inference_deepmedic'
PATH_TO_MEDPERF='/home/ubuntu/medperf'


docker pull $YOUR_DOCKER_CONTAINER

cd $PATH_TO_MEDPERF

medperf --storage=./medperf-env test -b 3

#echo 'Please check the $PATH_TO_MEDPERF/medperf-env/results folder to get your results'

echo '**************************** END ***************************************'
