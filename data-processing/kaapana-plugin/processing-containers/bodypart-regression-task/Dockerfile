FROM local-only/base-python-gpu:latest

LABEL IMAGE="bodypartregression-task-api"
LABEL VERSION="1.0.0"
LABEL BUILD_IGNORE="False"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /kaapana/app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Keep this source and model pin in sync with the legacy BodyPartRegression image.
RUN git clone https://github.com/MIC-DKFZ/BodyPartRegression.git \
    && cd BodyPartRegression \
    && git checkout 7f66baa

RUN touch BodyPartRegression/src/models/public_bpr_model.zip
RUN curl --location \
    --header "Connection: Keep-Alive" \
    --header "Keep-Alive: 300" \
    "https://zenodo.org/record/5113483/files/public_bpr_model.zip?download=1" \
    -o /kaapana/app/BodyPartRegression/src/models/public_bpr_model.zip
RUN echo "cc0ba26374932f0ca27452f4ad9bf9db  /kaapana/app/BodyPartRegression/src/models/public_bpr_model.zip" \
    | md5sum -c -
RUN unzip BodyPartRegression/src/models/public_bpr_model.zip \
    -d /kaapana/app/BodyPartRegression/src/models/

RUN pip3 uninstall -y torch torchtext torchaudio \
    && pip3 install \
        -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt \
        /kaapana/app/BodyPartRegression/ \
    && pip3 install pytorch-lightning==2.6.5

# Fix CVE-2024-8019/CVE-2024-8020 (critical): force patched pytorch-lightning.
RUN pip3 install \
    -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt \
    "pytorch-lightning==2.4.0"

COPY processing-container.json /processing-container.json
COPY files/run_bpreg.py /kaapana/app/run_bpreg.py

WORKDIR /kaapana/app/BodyPartRegression

CMD ["python3", "-u", "/kaapana/app/run_bpreg.py", "--gpu"]
