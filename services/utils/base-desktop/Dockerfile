# Pinned selkies commit — the single source of truth for BOTH the web dashboard (built from
# source in the selkies-frontend stage below) and the python server (pip-installed in the final
# stage). Bump this one value to move the whole streaming stack.
ARG SELKIES_COMMIT=0d134b6e1ffe42a579bc66363b0e7159ab22aacc

# Build the Selkies web dashboard (React/Vite SPA) from ${SELKIES_COMMIT}. The SPA is not part of
# the pip package and is not published as a release artifact, so it must be built from source
# (this mirrors the LinuxServer frontend build we previously copied the prebuilt dashboard from).
FROM alpine:3.22 AS selkies-frontend
ARG SELKIES_COMMIT
RUN apk add --no-cache cmake git nodejs npm
RUN git clone https://github.com/selkies-project/selkies.git /src \
    && cd /src && git checkout -f ${SELKIES_COMMIT}
# selkies-web-core is a shared library the dashboard imports, so it must be built first; the
# trailing test guards against an upstream SPA layout change (the build fails loudly instead of
# shipping a broken dashboard).
RUN cd /src/addons/selkies-web-core && npm install && npm run build \
    && cd /src/addons/selkies-dashboard \
    && cp ../selkies-web-core/dist/selkies-core.js src/ \
    && npm install && npm run build \
    && mkdir -p dist/src dist/nginx \
    && cp ../selkies-web-core/dist/selkies-core.js dist/src/ \
    && cp ../universal-touch-gamepad/universalTouchGamepad.js dist/src/ \
    && cp ../selkies-web-core/nginx/* dist/nginx/ \
    && cp -r ../selkies-web-core/dist/jsdb dist/ \
    && test -f dist/index.html && test -f dist/src/selkies-core.js

# Build libva >= 2.22 (core lib only) from source. pixelflux's bundled FFmpeg 8 references the
# vaMapBuffer2 symbol (libva 2.22), but the Ubuntu 24.04 base ships libva 2.20, so
# screen_capture_module.so fails to dlopen without a newer core libva. Building it here (was
# previously copied by digest from the LinuxServer selkies image) keeps the image self-contained.
# NOTE: after any future pixelflux bump, re-test whether this is still needed — a newer bundled
# FFmpeg may drop the vaMapBuffer2 dependency and let this whole stage be removed.
FROM ubuntu:24.04 AS libva-builder
ARG LIBVA_VERSION=2.22.0
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl meson ninja-build build-essential pkg-config libdrm-dev \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL "https://github.com/intel/libva/archive/refs/tags/${LIBVA_VERSION}.tar.gz" | tar -xz -C /tmp \
    && cd /tmp/libva-${LIBVA_VERSION} \
    && meson setup build --prefix=/usr --libdir=lib/x86_64-linux-gnu \
    && ninja -C build \
    && DESTDIR=/out meson install -C build \
    && cp -L /out/usr/lib/x86_64-linux-gnu/libva.so.2 /libva.so.2.real

FROM local-only/base-python-gpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-desktop"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        apache2-utils \
        arc-theme \
        at-spi2-core \
        ca-certificates \
        curl \
        dbus-x11 \
        gnome-themes-extra \
        # gnome-themes-standard \
        gnupg \
        gpg-agent \
        gpgconf \
        gtk2-engines-murrine \
        gtk2-engines-pixbuf \
        jgmenu \
        libgl1-mesa-dri \
        libglu1-mesa-dev \
        libgomp1 \
        libqt5opengl5-dev \
        libqt5svg5-dev \
        libqt5webengine-data \
        libqt5x11extras5-dev \
        libqt5xmlpatterns5-dev \
        libssl-dev \
        libtiff5-dev \
        libwrap0-dev \
        libxcb-cursor0 \
        libxcomposite1 \
        libxcursor1 \
        libxi-dev \
        libxkbcommon-x11-0 \
        libxt-dev \
        linux-libc-dev \
        lxde \
        mesa-common-dev \
        net-tools \
        psmisc \
        python3-pip \
        qtbase5-dev \
        qtscript5-dev \
        qttools5-dev \
        qtwebengine5-dev \
        qtxmlpatterns5-dev-tools \
        software-properties-common \
        sudo \
        supervisor \
        tint2 \
        ttf-wqy-zenhei \
        vim-tiny \
        webp-pixbuf-loader \
        wmctrl \
        x11-utils \
        xvfb \
        xz-utils \
        nginx \
        xcvt \
        pulseaudio \
        pulseaudio-utils \
        xclip \
        xdotool \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Chromium (open source). The Ubuntu 24.04 `chromium`/`chromium-browser` apt packages are snap
# transitional stubs that can't run in a container, so pull a real .deb from the xtradeb PPA
# (software-properties-common, for add-apt-repository, is already installed above). The package
# ships /usr/share/applications/chromium.desktop, so it appears in the LXDE menu under Internet;
# inject --no-sandbox into its Exec since chromium's sandbox can't initialise as a non-root user
# in the pod. The trailing grep guards the sed target so the build fails loudly if it stops matching.
# --no-sandbox triggers a security warning banner on every launch; it is suppressed via the managed
# policy shipped at files/etc/chromium/policies/managed/kaapana-policies.json.
RUN add-apt-repository -y ppa:xtradeb/apps \
    && apt-get update \
    && apt-get install -y --no-install-recommends chromium \
    && sed -i 's|^Exec=/usr/bin/chromium |Exec=/usr/bin/chromium --no-sandbox |' /usr/share/applications/chromium.desktop \
    && grep -q '^Exec=/usr/bin/chromium --no-sandbox ' /usr/share/applications/chromium.desktop \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# tini to fix subreap
ARG TINI_VERSION=v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /bin/tini
RUN chmod +x /bin/tini

# Selkies v2 streaming: web frontend (SPA) built from ${SELKIES_COMMIT} in the selkies-frontend
# stage above (previously copied by digest from the LinuxServer selkies image). The python
# websocket server is installed from the same commit further down, so both stay coherent.
COPY --from=selkies-frontend /src/addons/selkies-dashboard/dist /usr/share/selkies/selkies-dashboard

# Newer core libva (built from source in the libva-builder stage above) so pixelflux's FFmpeg 8
# path can dlopen: it needs libva >= 2.22 (symbol vaMapBuffer2) but the base ships 2.20, so
# screen_capture_module.so fails to dlopen even with CPU encoding. Only the core lib is swapped
# and the SONAME pointed at it; the drm/x11 backends stay at the base's 2.20.
COPY --from=libva-builder /libva.so.2.real /usr/lib/x86_64-linux-gnu/libva.so.2.2200.0
RUN ln -sf libva.so.2.2200.0 /usr/lib/x86_64-linux-gnu/libva.so.2 && ldconfig

# Selkies server (pixelflux/websocket mode), installed from the same ${SELKIES_COMMIT} that built
# the dashboard above. flux versions are pinned separately because selkies' pyproject leaves them
# unpinned. evdev + xkbcommon are sdist-only, so install the dev headers to build them and purge
# again in the same layer (build-essential is already in the base).
ARG SELKIES_COMMIT
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-dev libxkbcommon-dev pkg-config \
    && python3 -m pip install --no-cache-dir \
        "selkies @ git+https://github.com/selkies-project/selkies.git@${SELKIES_COMMIT}" \
        pixelflux==1.6.2 \
        pcmflux==1.0.8 \
    && apt-get purge -y python3-dev libxkbcommon-dev pkg-config \
    && apt-get autoremove -y && apt-get autoclean -y && rm -rf /var/lib/apt/lists/*

# The Selkies web client sends the display DPI as 96 * devicePixelRatio (e.g. 192 on a retina
# client). We always run with --use-css-scaling, which already applies the devicePixelRatio via a
# stretched canvas, so honouring that DPI double-scales and every toolkit renders 2x-oversized
# fonts. Pin the applied DPI to 96 (correct for css-scaling on any client; a no-op at DPR 1) by
# forcing it in set_dpi(), the single chokepoint every DPI path funnels through (both the client
# "s," message and the client-settings handler) — this covers xrdb, xsettingsd and xfconf at once.
# The trailing grep is a guard: if the sed target ever stops matching, the build fails loudly
# instead of silently shipping oversized fonts.
RUN SELKIES_PY="$(python3 -c 'import selkies, os; print(os.path.join(os.path.dirname(selkies.__file__), "selkies.py"))')" \
    && sed -i 's|        dpi_value = int(str(dpi_setting))|        dpi_value = 96  # Kaapana: css-scaling already applies devicePixelRatio; pin 96 to avoid double-scaled fonts|' "$SELKIES_PY" \
    && grep -q 'dpi_value = 96  # Kaapana' "$SELKIES_PY"

# pixelflux uses hardware H.264 (NVENC) when it can dlopen libnvidia-encode, which the NVIDIA
# container runtime only injects when the "video" driver capability is requested. The GPU base
# image sets only compute,utility, so widen it here to include video; startup.sh then switches
# selkies to the NVENC encoder when a GPU is present. No effect on CPU-only launches.
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,video

# Default text editor (mousepad) + PDF viewer (qpdfview) for the desktop, installed explicitly
# rather than relying on a transitive dependency, so the .txt / .pdf handlers wired in
# files/usr/share/applications/mimeapps.list always resolve. qpdfview is a lightweight Qt viewer
# (pulls poppler as a hard dep) — chosen over okular to avoid dragging the full KF5/phonon stack in.
RUN apt-get update \
    && apt-get install -y --no-install-recommends mousepad qpdfview \
    && apt-get autoclean -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY /files/etc /etc
COPY /files/root /root
COPY /files/usr /usr

# kaapana menu launcher icon (brain mark, reused from the noVNC loading logo)
COPY files/logo.png /usr/share/kaapana/kaapana.png

# browser-tab favicon for the streamed app: the kaapana "brain in a desktop" app icon (the same
# favicon the noVNC page used). The Selkies dashboard references icon.png but ships none.
COPY files/favicon.png /usr/share/selkies/selkies-dashboard/icon.png

# single desktop (removes the workspace pager view) + flat dark openbox window decorations
RUN sed -i \
        -e 's|<number>4</number>|<number>1</number>|' \
        -e 's|<name>Clearlooks</name>|<name>Kaapana-Dark</name>|' \
        /etc/xdg/openbox/rc.xml

# register the webp gdk-pixbuf loader so pcmanfm can render the .webp wallpaper
RUN /usr/lib/x86_64-linux-gnu/gdk-pixbuf-2.0/gdk-pixbuf-query-loaders --update-cache

# Desktop-environment tweaks for the streamed desktop:
#  - quick_exec=1: the "this .desktop is an executable script, run it?" prompt is a *libfm* dialog,
#    so the setting must live in libfm.conf (pcmanfm.conf is set too, harmless) — this lets a
#    Desktop launcher run without confirmation, matching the start-menu entry.
#  - "Radiology" start-menu group: apps opt in with Categories=Radiology (see Radiology.directory,
#    shipped above). Inserted into the main lxde menu — deterministic, no merge-dir basename guess.
# Each step self-guards (grep / assert) so a layout change upstream fails the build, not silently.
RUN sed -i '/^\[config\]/a quick_exec=1' /etc/xdg/libfm/libfm.conf \
    && sed -i '/^\[config\]/a quick_exec=1' /etc/xdg/pcmanfm/LXDE/pcmanfm.conf \
    && grep -q '^quick_exec=1' /etc/xdg/libfm/libfm.conf \
    && python3 -c "p='/etc/xdg/menus/lxde-applications.menu'; s=open(p).read(); b='\t<Menu>\n\t\t<Name>Radiology</Name>\n\t\t<Directory>Radiology.directory</Directory>\n\t\t<Include>\n\t\t\t<And>\n\t\t\t\t<Category>Radiology</Category>\n\t\t\t</And>\n\t\t</Include>\n\t</Menu>\n'; i=s.rfind('</Menu>'); assert i>=0, 'no </Menu> in menu'; open(p,'w').write(s[:i]+b+s[i:]); assert 'Radiology.directory' in open(p).read()"

EXPOSE 80
WORKDIR /root
ENV HOME=/root \
    SHELL=/bin/bash

# Default User
ENV USER=researcher
RUN useradd -m $USER -s /bin/bash -u 1000 -G sudo \
    && echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$USER \
    && su $USER -c "mkdir -p /home/researcher/Desktop" \
    && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

# Note: if sudo access should not be possible in derived containers:
# RUN  rm /etc/sudoers.d/$USER

COPY files/startup.sh /startup.sh
ENTRYPOINT ["/startup.sh"]