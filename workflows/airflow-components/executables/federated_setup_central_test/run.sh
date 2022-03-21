#!/bin/bash
set -euf -o pipefail

echo 'Converting jupyter notebook file'
jupyter nbconvert --to python /executables/federated_setup_central_test/run_federated_setup_central_test.ipynb    
echo 'Executing python script'
python3 /executables/federated_setup_central_test/run_federated_setup_central_test.py