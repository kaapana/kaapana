FROM local-only/base-python-cpu:latest

LABEL IMAGE="combine-masks"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/combine_masks.py"]
