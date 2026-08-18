FROM local-only/base-python-cpu:latest

LABEL IMAGE="seg-eval"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN python3 -m pip install -c /constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt && rm /kaapana/app/requirements.txt 

COPY files/opensearch_helper.py /kaapana/app/
COPY files/start.py /kaapana/app/
COPY files/eval.py /kaapana/app/
COPY files/eval_nnunet_predict.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
