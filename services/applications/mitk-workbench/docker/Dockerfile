FROM local-only/base-mitk:latest AS mitk-image
FROM local-only/base-desktop:latest

LABEL IMAGE="mitk-workbench"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

# browser-tab title -> "Kaapana App - MITK Workbench" (startup.sh writes the dashboard manifest)
ENV KAAPANA_APP_NAME="MITK Workbench"

COPY --from=mitk-image /kaapana/app/ /mitk/

RUN ln -s /kaapana/minio /home/$USER/Desktop/data
WORKDIR /kaapana/minio

COPY files/startMITK.sh /mitk/
COPY files/launch-mitk.sh /mitk/
COPY files/supervisord-mitk.conf /etc/supervisor/conf.d/

# Desktop + start-menu launcher icon: the official MITK app icon, pinned to the same release tag
# as the bundled MITK (v2025.12.2, see base-mitk) — referenced by mitk.desktop.
RUN mkdir -p /usr/share/kaapana \
    && curl -k -sS -L -f -C - --retry 20 --retry-all-errors --retry-delay 10 \
      -o /usr/share/kaapana/mitk-logo.png \
      "https://raw.githubusercontent.com/MITK/MITK/v2025.12.2/Applications/Workbench/icons/icon.png"
COPY files/mitk.desktop /usr/share/applications/mitk.desktop
COPY files/mitk.desktop /home/$USER/Desktop/mitk.desktop
RUN chmod +x /mitk/launch-mitk.sh /home/$USER/Desktop/mitk.desktop \
    && chown $USER:$USER /home/$USER/Desktop/mitk.desktop

# Skip the "Welcome to MITK Workbench" startup dialog + intro by pre-seeding the BlueBerry prefs.
# The state path's hash derives from the fixed install dir (/mitk) so it is stable for this image;
# if MITK's version/layout changes the dialog simply reappears (soft failure, not a build break).
COPY files/mitk-prefs.xml /tmp/mitk-prefs.xml
RUN mkdir -p "/home/$USER/.local/share/DKFZ/MITK Workbench_9177497765956760190/data/3" \
    && cp /tmp/mitk-prefs.xml "/home/$USER/.local/share/DKFZ/MITK Workbench_9177497765956760190/data/3/prefs.xml" \
    && rm /tmp/mitk-prefs.xml \
    && chown -R $USER:$USER "/home/$USER/.local/share/DKFZ"

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
