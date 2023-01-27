FROM local-only/base-python-cpu:latest

LABEL IMAGE="monai-get-models"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

RUN python3 -m pip install -q "monai[nibabel,itk,tqdm,pandas,skimage]"

COPY files/process.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/process.py"]