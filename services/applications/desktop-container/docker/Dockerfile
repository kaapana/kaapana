FROM local-only/base-mitk:latest AS mitk-image
FROM local-only/base-desktop:latest

LABEL IMAGE="desktop-container"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

# browser-tab title -> "Kaapana App - Desktop" (startup.sh writes the dashboard manifest)
ENV KAAPANA_APP_NAME="Desktop"

RUN ln -s /kaapana/minio /home/$USER/Desktop/data
WORKDIR /kaapana/minio

# As an kaapana admin, you can build and install software here, that should be part of
# the desktop-container.

# CLI tools + a browser-launchable game + LibreOffice (office suite; writer/calc/impress
# self-register their own menu launchers), plus the runtime libs 3D Slicer needs
# (same xcb/nss/pulse set as slicer-workbench, which shares this base-desktop image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        dcmtk \
        git \
        libreoffice-writer \
        libreoffice-calc \
        libreoffice-impress \
        supertuxkart \
        libpulse-dev \
        libglu1-mesa \
        libnss3 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-render-util0 \
        libxcb-xkb1 \
        libxkbcommon-x11-0 \
        libxcb-shape0 \
        libxcb-xinerama0 \
        libxcb-randr0 \
        xauth \
    && rm -rf /var/lib/apt/lists/*

# apt installs games under /usr/games, which isn't on the desktop session PATH; add it so
# supertuxkart's launcher (Exec=supertuxkart) resolves.
ENV PATH="/usr/games:${PATH}"

# napari — scientific n-dimensional image viewer. Installed in its OWN venv: napari needs a
# newer pydantic-settings than the shared /opt/venv can carry (kaapana-client pins pydantic
# ==2.7.4), and mixing them breaks napari at startup (FileConfigSettingsSource.current_state).
RUN python3 -m venv /opt/napari-venv \
    && /opt/napari-venv/bin/pip install --no-cache-dir "napari[pyqt5]"

# 3D Slicer 5.8.1 (same pinned build as slicer-workbench)
RUN set -eux; \
    SLICER_URL="https://download.slicer.org/bitstream/67c51fc129825655577cfee9"; \
    curl -k -sS -L -f -C - --retry 20 --retry-all-errors --retry-delay 10 \
      -o /tmp/slicer.tar.gz "$SLICER_URL"; \
    tar -xzf /tmp/slicer.tar.gz -C /tmp; \
    mv /tmp/Slicer* /opt/slicer; \
    rm -f /tmp/slicer.tar.gz; \
    chmod -R a+w /opt/slicer

# MITK Workbench — reuse the prebuilt MITK from base-mitk (base build only, no nnInteractive)
COPY --from=mitk-image /kaapana/app/ /mitk/

# QuPath 0.7.0 — whole-slide / digital-pathology analysis (jpackage app-image, bundles its own JRE)
RUN set -eux; \
    QUPATH_URL="https://github.com/qupath/qupath/releases/download/v0.7.0/QuPath-v0.7.0-Linux.tar.xz"; \
    curl -k -sS -L -f -C - --retry 20 --retry-all-errors --retry-delay 10 \
      -o /tmp/qupath.tar.xz "$QUPATH_URL"; \
    tar -xJf /tmp/qupath.tar.xz -C /opt; \
    rm -f /tmp/qupath.tar.xz; \
    mv /opt/QuPath /opt/qupath; \
    chmod -R a+w /opt/qupath

# napari ships only an .ico/SVG logo; render a PNG launcher icon using napari's own bundled Pillow.
RUN mkdir -p /usr/share/pixmaps \
    && /opt/napari-venv/bin/python3 -c "import glob; from PIL import Image; Image.open(glob.glob('/opt/napari-venv/lib/python*/site-packages/napari/resources/icon.ico')[0]).save('/usr/share/pixmaps/napari.png')"

# MITK launcher icon: the official MITK app icon, pinned to the same release tag as the bundled
# MITK (v2025.12.2, see base-mitk). Square (menus/openbox squish a wide wordmark) — referenced by
# mitk.desktop as /usr/share/pixmaps/mitk.png.
RUN mkdir -p /usr/share/pixmaps \
    && curl -k -sS -L -f -C - --retry 20 --retry-all-errors --retry-delay 10 \
      -o /usr/share/pixmaps/mitk.png \
      "https://raw.githubusercontent.com/MITK/MITK/v2025.12.2/Applications/Workbench/icons/icon.png"

# Desktop/menu launchers for the GUI apps not on PATH (jgmenu's `lx` reads /usr/share/applications;
# also drop copies on the Desktop, where a Desktop-Demo user lands). qpdfview self-registers.
COPY files/usr /usr
RUN chmod +x /usr/local/bin/launch-mitk.sh \
    && mkdir -p /home/$USER/Desktop \
    && cp /usr/share/applications/napari.desktop \
          /usr/share/applications/3dslicer.desktop \
          /usr/share/applications/mitk.desktop \
          /usr/share/applications/qupath.desktop \
          /usr/share/applications/chromium.desktop \
          /usr/share/applications/libreoffice-writer.desktop \
          /usr/share/applications/libreoffice-calc.desktop \
          /usr/share/applications/libreoffice-impress.desktop \
          /home/$USER/Desktop/ \
    && chmod +x /home/$USER/Desktop/*.desktop \
    && chown -R $USER:$USER /home/$USER/Desktop
