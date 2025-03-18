FROM local-only/base-python-cpu:latest

LABEL IMAGE="send-to-faiss"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

RUN apt-get update && apt-get install -y xvfb

COPY files/requirements.txt /kaapana/app/requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r /kaapana/app/requirements.txt

# RUN apt-get install -y git-lfs && \
#     git lfs install

# RUN mkdir -p /kaapana/app/models && \
#     cd /kaapana/app/models && \
#     git lfs install && \
#     git clone https://huggingface.co/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224 && \
#     cd /kaapana/app/models/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224 && \
#     git lfs pull

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/send_to_faiss.py"]
