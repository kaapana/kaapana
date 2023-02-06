# FROM local-only/base-python-alpine:latest
FROM local-only/base-python-cpu:latest

LABEL IMAGE="monai-get-models"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

# COPY files/requirements.txt /kaapanasrc/

RUN python -m pip install "monai[nibabel,itk,tqdm,pandas,skimage]"
# RUN pip3 install —upgrade pip \
#     && pip install "monai[nibabel,itk,tqdm,pandas,skimage]"
# RUN pip install --upgrade pip \
#     && pip install -r /kaapanasrc/requirements.txt
# RUN python -m pip install --upgrade pip \
#     && pip3 install -r /kaapanasrc/requirements.txt

# # Code server
# RUN wget https://code-server.dev/install.sh
# RUN /bin/bash install.sh --version 4.2.0
# RUN code-server --install-extension ms-python.python

ENV MODELDIR "/models"

COPY files/get-monai-models.py /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/get-monai-models.py"]