FROM local-only/base-nnunet-v2:latest

LABEL IMAGE="liver-tumor-segmentation"
LABEL VERSION="1.0.0"
LABEL CI_IGNORE="True"

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /
RUN python3 -m pip install nnunetv2
COPY STU-Net /STU-Net

RUN python3 -m pip install blosc2 
RUN python3 -m pip install matplotlib==3.7.3
RUN git clone https://github.com/MIC-DKFZ/acvl_utils.git -b v0.2
RUN python3 -m pip install ./acvl_utils

ENV nnUNet_raw='/STU-Net/nnUNET_raw_data'
ENV nnUNet_preprocessed='/STU-Net/nnUNET_preprocessed'
ENV nnUNet_results='/STU-Net/nnUNET_results'

COPY /STU-Net/nnUNet-2.2/nnunetv2/ /opt/venv/lib/python3.12/site-packages/nnunetv2/

RUN wget -O /STU-Net/nnUNET_results/Dataset123_ATLAS/STUNetTrainer_base_ft__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth https://heibox.uni-heidelberg.de/f/327ee31cf8f84ba6be16/?dl=1

CMD ["python3", "/STU-Net/kaapana_file_provider.py"]
