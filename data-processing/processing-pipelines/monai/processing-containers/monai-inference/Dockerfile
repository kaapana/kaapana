FROM local-only/base-python-gpu:latest

LABEL IMAGE="monai-inference"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /kaapanasrc/

# RUN python -m pip install "monai[nibabel,itk,tqdm,pandas,skimage]"
RUN pip3 install --upgrade pip \
    && pip3 install -r /kaapanasrc/requirements.txt

ENV MODELDIR "/models"

COPY files/monai-inference_cmd.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/monai-inference_cmd.py"]