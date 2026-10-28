FROM local-only/base-nnunet:latest

LABEL IMAGE="nnunetv2"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

# nnFoundation checkpoints (https://huggingface.co/MIC-DKFZ, CC-BY-SA-4.0) ship with the image because most
# platforms have no internet access. Pinned revisions; this layer comes before the code so that code changes
# neither download nor push the ~3 GB again.
ARG NNFOUNDATION_CNN_REVISION=f443c09319988e833b3d9589bf95909e4443d7b2
ARG NNFOUNDATION_VIT_REVISION=c691f2115140458ec64017712eb8ebbc8dde6ae4
ENV NNUNET_BUNDLED_PRETRAINED=/opt/nnunet-pretrained
RUN python3 -c "\
from huggingface_hub import hf_hub_download; \
pins = {'MIC-DKFZ/nnFoundationCNN': '${NNFOUNDATION_CNN_REVISION}', 'MIC-DKFZ/nnFoundationViT': '${NNFOUNDATION_VIT_REVISION}'}; \
[hf_hub_download(repo_id=r, filename=f, revision=v, local_dir='${NNUNET_BUNDLED_PRETRAINED}/' + r.replace('/', '_')) \
 for r, v in pins.items() for f in ('adaptation_plan.json', 'checkpoint_final.pth', 'config.json', 'README.md')]" \
    && rm -rf ${NNUNET_BUNDLED_PRETRAINED}/*/.cache && chmod -R a+rX ${NNUNET_BUNDLED_PRETRAINED}

COPY files/kaapana_nnunet /opt/kaapana_nnunet
RUN pip3 install -c /constraints.txt /opt/kaapana_nnunet

# every pod sees its nnU-Net folders at the same absolute paths (see kaapana_nnunet.layout)
RUN mkdir -p /nnunet && chmod 777 /nnunet

ENV nnUNet_n_proc_DA=12
ENV PYTHONUNBUFFERED=1

WORKDIR /kaapana/app
ENTRYPOINT ["python3", "-m", "kaapana_nnunet"]
