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

# nnInteractive setup — installed under /opt (OUTSIDE $HOME) so base-desktop's
# startup `chown -R $HOME` doesn't copy-up ~7GB on overlayfs on every container start.
# Symlinks preserve the paths MITK/huggingface expect; installing as $USER keeps the
# files runtime-owned without a post-hoc chown that would double the image layer.
# Note: B2B4C0D1C161C0A7 is fixed hash of path. Needs change only when MITK's location in the container is changed.
ENV HF_HOME=/opt/nninteractive/huggingface
RUN mkdir -p /opt/nninteractive /home/$USER/.local/share /home/$USER/.cache \
    && ln -s /opt/nninteractive/mitk_venvs  /home/$USER/.local/share/mitk_venvs \
    && ln -s /opt/nninteractive/huggingface /home/$USER/.cache/huggingface \
    && chown -R $USER:$USER /opt/nninteractive
USER $USER
WORKDIR /opt/nninteractive
RUN /mitk/python/bin/python3 -m venv ./mitk_venvs/B2B4C0D1C161C0A7/nnInteractive
RUN . ./mitk_venvs/B2B4C0D1C161C0A7/nnInteractive/bin/activate && pip install --no-cache-dir torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu118
RUN . ./mitk_venvs/B2B4C0D1C161C0A7/nnInteractive/bin/activate && pip install --no-cache-dir "nnInteractive>=1.1.2,<2.0.0"
RUN . ./mitk_venvs/B2B4C0D1C161C0A7/nnInteractive/bin/activate && \
        python -c "from huggingface_hub import snapshot_download;\
        repo_id = 'nnInteractive/nnInteractive'; \
        download_path = snapshot_download(repo_id=repo_id, allow_patterns=['nnInteractive_v1.0/*'], force_download=False);"
USER root
