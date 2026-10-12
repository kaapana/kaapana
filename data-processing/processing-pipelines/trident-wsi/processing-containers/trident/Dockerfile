FROM local-only/base-python-gpu:latest

LABEL IMAGE="trident"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

# System libs: git for cloning; libvips42 for the pyvips binding (TRIDENT's own core dependency -
# unlike openslide-bin, plain pyvips wheels do NOT bundle libvips itself); libgl1 already comes from
# base-python-gpu (covers opencv's GUI-variant GL dependency).
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    git \
    libvips42 \
    && rm -rf /var/lib/apt/lists/*

# --- TRIDENT: clone the OFFICIAL upstream repo (not a project-specific fork) ---
# Pin a specific commit for build reproducibility. Update this when intentionally upgrading TRIDENT.
ARG TRIDENT_GIT_REF=main
ARG TRIDENT_REPO=https://github.com/mahmoodlab/trident.git
RUN git clone --branch ${TRIDENT_GIT_REF} --depth 1 ${TRIDENT_REPO} /opt/trident

# Add the new DICOM-WSI reader backend and register it in TRIDENT's reader factory.
COPY files/dicom_wsi_patch/DicomWSI.py /opt/trident/trident/wsi_objects/DicomWSI.py
COPY files/dicom_wsi_patch/apply_patch.py /tmp/apply_patch.py
RUN python3 /tmp/apply_patch.py /opt/trident/trident/wsi_objects/WSIFactory.py

# Install our own pins FIRST (notably timm==0.9.16 - TRIDENT's own pyproject.toml only requires
# ">=0.9.16,<2", a range wide enough to let pip pick a newer timm that TRIDENT's own README says
# breaks most encoders; pre-installing the exact pin means the later -e install's wider constraint
# is already satisfied and pip leaves it alone), then let `pip install -e .` (deliberately WITHOUT
# --no-deps this time) resolve and install the rest of TRIDENT's own declared dependencies itself,
# rather than hand-duplicating its full pyproject.toml dependency list here (which drifts out of
# sync with upstream - torch/torchvision are left alone since base-python-gpu already satisfies
# TRIDENT's unconstrained "torch = *"/"torchvision = *").
COPY files/requirements.txt /kaapana/app/requirements.txt
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt
RUN python -m pip install --no-cache-dir -e /opt/trident

# Optional PoC bake-in path: any checkpoints dropped here are picked up by TRIDENT's local_ckpts.json
# registry mechanism so a deployment can skip the HuggingFace download entirely for those models.
COPY files/local_ckpts/ /opt/trident_local_ckpts/

ENV TRIDENT_HOME=/opt/trident_cache

COPY files/*.py /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/start.py"]
