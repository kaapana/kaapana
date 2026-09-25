# base-python-gpu: this image needs torch (kaapana_federated / monai), which the CPU base no longer carries.
FROM local-only/base-python-gpu:latest

LABEL IMAGE="dice-evaluation"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /
RUN pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt --no-cache-dir -r /requirements.txt

COPY files/start.py /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/start.py"]