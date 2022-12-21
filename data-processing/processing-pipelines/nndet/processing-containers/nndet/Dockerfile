FROM local-only/base-nndet:latest

LABEL IMAGE="nndet-gpu"
LABEL VERSION="11-22"
LABEL CI_IGNORE="False"

RUN pip install packaging==21.00

COPY files/ /kaapanasrc/
WORKDIR /kaapanasrc/
CMD ["python3", "-u", "/kaapanasrc/nndet_predict_kaapana.py"]