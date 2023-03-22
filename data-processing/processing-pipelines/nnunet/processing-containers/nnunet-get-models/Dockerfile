FROM local-only/base-python-cpu:latest

LABEL IMAGE="nnunet-get-models"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

ENV MODELDIR "/models"

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/develop/build-scripts/constraints-0.1.3.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/process.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/process.py"]