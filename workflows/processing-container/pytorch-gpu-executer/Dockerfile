FROM local-only/base-pytorch-gpu:0.1.0

LABEL IMAGE="pytorch-gpu-executer"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

# Only for jupyternotebook: jupyter nbconvert --to html --no-input ...
RUN apt-get update && apt-get install -y texlive-xetex texlive-fonts-recommended texlive-plain-generic pandoc \
    && rm -rf /var/lib/apt/lists/*