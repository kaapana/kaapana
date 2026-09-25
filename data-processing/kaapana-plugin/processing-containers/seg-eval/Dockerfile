# base-python-gpu: this image needs torch (kaapana_federated / monai), which the CPU base no longer carries.
FROM local-only/base-python-gpu:latest

LABEL IMAGE="seg-eval"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt && rm /kaapana/app/requirements.txt 

COPY files/opensearch_helper.py /kaapana/app/
COPY files/start.py /kaapana/app/
COPY files/eval.py /kaapana/app/
COPY files/eval_nnunet_predict.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
