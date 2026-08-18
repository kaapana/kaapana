FROM local-only/base-python-cpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-model-installer"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/provide_models.py /kaapana/app/provide_models.py
COPY files/requirements.txt /kaapana/app/

COPY --from=constraints 0.7.0.txt /constraints.txt
RUN python -m pip install -c /constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

CMD ["python3","-u","/kaapana/app/provide_models.py", "-e"]
