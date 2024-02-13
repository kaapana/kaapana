FROM local-only/base-nnunet:latest

LABEL IMAGE="nnunet-gpu"
LABEL VERSION="03-22"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/
WORKDIR /kaapana/app/
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.1/build-scripts/constraints-0.2.1.txt --upgrade setuptools pip && pip3 install -r /kaapana/app/requirements.txt

CMD ["bash","/kaapana/app/start_nnunet.sh"]