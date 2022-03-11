#!/bin/bash
set -euf -o pipefail

echo 'Converting jupyter notebook file'
jupyter nbconvert --to python /executables/nnunet_federated/run_nnunet_federated.ipynb    
echo 'Executing python script'
python3 /executables/nnunet_federated/run_nnunet_federated.py