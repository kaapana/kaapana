FROM local-only/base-python-cpu:latest

LABEL IMAGE="dcmstruct2nifti"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/start.py /kaapana/app/
CMD ["python3","-u","/kaapana/app/start.py"]
