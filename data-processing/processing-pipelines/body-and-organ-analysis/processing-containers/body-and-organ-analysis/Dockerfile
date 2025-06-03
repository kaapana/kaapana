FROM local-only/base-python-cpu-3.10:latest AS poetry2requirements


RUN git clone https://github.com/UMEssen/Body-and-Organ-Analysis.git /Body-and-Organ-Analysis
WORKDIR /Body-and-Organ-Analysis
RUN git checkout 0a3a344
RUN ./scripts/generate_version.sh

ENV POETRY_HOME=/etc/poetry
RUN pip3 install poetry==1.3.2
RUN python3 -m poetry export -E "triton pacs" --without-hashes -f requirements.txt > /Requirements.txt

####################
# PROCESSING_IMAGE #
####################
FROM local-only/base-python-gpu-3.10:latest

LABEL IMAGE="body-and-organ-analysis"
LABEL VERSION="0.1.3"
LABEL BUILD_IGNORE="False"

COPY --from=poetry2requirements /Requirements.txt /tmp
RUN apt-get -y update; DEBIAN_FRONTEND=noninteractive apt-get -y install \
    jq curl ffmpeg libsm6 libxext6 libpangocairo-1.0-0 dcmtk xvfb libjemalloc2 nvidia-cuda-toolkit && rm -rf /var/lib/apt/lists/*

ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

ENV BOA_VERSION=0.1.3
ENV BOA_GITHASH=0a3a344
WORKDIR /app

COPY --from=poetry2requirements /Body-and-Organ-Analysis/pyproject.toml /Body-and-Organ-Analysis/README.md /app/
COPY --from=poetry2requirements /Body-and-Organ-Analysis/body_organ_analysis /app/body_organ_analysis

RUN chmod a+rwx -R /app && \
    python3 -m pip install -U pip && \
    python3 -m pip install -r /tmp/Requirements.txt && \
    rm /tmp/Requirements.txt && \
    ## python3 -m pip install pyradiomics && \
    python3 -m pip install .

ENV TOTALSEG_WEIGHTS_PATH=/models
ENV MPLCONFIGDIR=/app/configs
ENV nnUNet_USE_TRITON=0

COPY files/run_boa.sh /app/

CMD ["/bin/bash", "run_boa.sh"]