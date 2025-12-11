FROM local-only/base-mitk:latest AS mitk-image
FROM local-only/base-desktop:latest

LABEL IMAGE="mitk-workbench"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

COPY --from=mitk-image /kaapana/app/ /mitk/

RUN ln -s /kaapana/minio /home/$USER/Desktop/data
WORKDIR /kaapana/minio

COPY files/startMITK.sh /mitk/
COPY files/supervisord-mitk.conf /etc/supervisor/conf.d/

# nnInteractive setup
# Note: B2B4C0D1C161C0A7 is fixed hash of path. Needs change only when MITK's location in the container is changed.
WORKDIR /home/$USER/.local/share/
RUN /mitk/python/bin/python3 -m venv ./mitk_venvs/B2B4C0D1C161C0A7/nnInteractive
RUN . ./mitk_venvs/B2B4C0D1C161C0A7/nnInteractive/bin/activate && pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu118
RUN . ./mitk_venvs/B2B4C0D1C161C0A7/nnInteractive/bin/activate && pip install "nnInteractive>=1.1.2,<2.0.0"
RUN . ./mitk_venvs/B2B4C0D1C161C0A7/nnInteractive/bin/activate && \
        python -c "from huggingface_hub import snapshot_download;\
        repo_id = 'nnInteractive/nnInteractive'; \
        download_path = snapshot_download(repo_id=repo_id, allow_patterns=['nnInteractive_v1.0/*'], force_download=False);"
RUN mkdir -p /home/$USER/.cache/huggingface && mv /root/.cache/huggingface/ /home/$USER/.cache/
