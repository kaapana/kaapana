#!/bin/bash

log() { echo "[base-desktop $(date -u +%H:%M:%S)] $*"; }

log "startup: begin"

if [ -n "$OPENBOX_ARGS" ]; then
    sed -i "s#^command=/usr/bin/openbox\$#& ${OPENBOX_ARGS}#" /etc/supervisor/conf.d/supervisord.conf
fi

# Selkies encoder selection. The container is sometimes started with an NVIDIA GPU and sometimes
# not, so pick the encoder per launch: with an NVENC-capable GPU use hardware full-frame H.264
# (pixelflux offloads to NVENC), otherwise keep the CPU striped encoder (only changed stripes are
# encoded — far cheaper on CPU for a mostly-static desktop). Detection mirrors pixelflux: it
# dlopens libnvidia-encode.so, which is only present when the pod has a GPU and the "video" driver
# capability. Fail open: if detection or the swap misses, we stay on the CPU default in the conf.
SELKIES_CONF=/etc/supervisor/conf.d/supervisord.conf
if ldconfig -p 2>/dev/null | grep -q 'libnvidia-encode\.so'; then
    if grep -q -- '--encoder=x264enc-striped --use-cpu=true' "$SELKIES_CONF"; then
        sed -i 's|--encoder=x264enc-striped --use-cpu=true|--encoder=x264enc --use-cpu=false|' "$SELKIES_CONF"
        log "selkies: NVENC-capable GPU detected -> hardware full-frame H.264 encoder"
    else
        log "selkies: WARN NVENC GPU detected but expected CPU encoder flags not found; leaving conf as-is"
    fi
else
    log "selkies: no NVENC GPU detected -> CPU striped H.264 encoder"
fi

USER=${USER:-root}
HOME=/root
if [ "$USER" != "root" ]; then
    log "user: enabling custom user '$USER'"
    # useradd --create-home --shell /bin/bash --user-group --groups adm,sudo $USER
    # if [ -z "$PASSWORD" ]; then
    #     echo "  set default password to \"ubuntu\""
    #     PASSWORD=ubuntu
    # fi
    HOME=/home/$USER
    # echo "$USER:$PASSWORD" | chpasswd
    cp -r /root/{.config,.gtkrc-2.0,.asoundrc} ${HOME} 2>/dev/null
    # chown -R $USER:$USER ${HOME}
    # [ -d "/dev/snd" ] && chgrp -R adm /dev/snd
fi
sed -i -e "s|%USER%|$USER|g" -e "s|%HOME%|$HOME|g" /etc/supervisor/conf.d/*.conf

# home folder
if [ ! -x "$HOME/.config/pcmanfm/LXDE/" ]; then
    mkdir -p $HOME/.config/pcmanfm/LXDE/
    ln -sf /usr/local/share/lxde-wallpapers/desktop-items-0.conf $HOME/.config/pcmanfm/LXDE/
    log "home: first start, chown -R $HOME (this blocks nginx startup)"
    SECONDS=0
    chown -R $USER:$USER $HOME
    log "home: chown finished in ${SECONDS}s"
fi

# nginx workers
sed -i 's|worker_processes .*|worker_processes 1;|' /etc/nginx/nginx.conf

# nginx ssl
if [ -n "$SSL_PORT" ] && [ -e "/etc/nginx/ssl/nginx.key" ]; then
    log "nginx: enabling SSL on port $SSL_PORT"
	sed -i 's|#_SSL_PORT_#\(.*\)443\(.*\)|\1'$SSL_PORT'\2|' /etc/nginx/sites-enabled/default
	sed -i 's|#_SSL_PORT_#||' /etc/nginx/sites-enabled/default
fi

# nginx http base authentication
if [ -n "$HTTP_PASSWORD" ]; then
    log "nginx: enabling HTTP basic authentication"
    htpasswd -bc /etc/nginx/.htpasswd $USER $HTTP_PASSWORD
	sed -i 's|#_HTTP_PASSWORD_#||' /etc/nginx/sites-enabled/default
fi

if [ -n "$INGRESS_PATH" ]; then
    if [[ $INGRESS_PATH == /* ]];
    then
        RELATIVE_URL_ROOT="${INGRESS_PATH:1}"
    else
        RELATIVE_URL_ROOT="$INGRESS_PATH"
    fi
    log "ingress: RELATIVE_URL_ROOT=$RELATIVE_URL_ROOT"
fi

# dynamic prefix path renaming
if [ -n "$RELATIVE_URL_ROOT" ]; then
    log "nginx: enabling RELATIVE_URL_ROOT=$RELATIVE_URL_ROOT"
	sed -i 's|#_RELATIVE_URL_ROOT_||' /etc/nginx/sites-enabled/default
	sed -i 's|_RELATIVE_URL_ROOT_|'$RELATIVE_URL_ROOT'|' /etc/nginx/sites-enabled/default
fi

# browser-tab title: the Selkies dashboard sets document.title from manifest.json's "name"
# (falling back to "Selkies" when the file is absent). Write it so the tab reads
# "Kaapana App - <app>", or just "Kaapana App" when the image sets no KAAPANA_APP_NAME.
DASHBOARD=/usr/share/selkies/selkies-dashboard
if [ -d "$DASHBOARD" ]; then
    APP_TAB_TITLE="Kaapana App"
    [ -n "$KAAPANA_APP_NAME" ] && APP_TAB_TITLE="Kaapana App - $KAAPANA_APP_NAME"
    printf '{"name":"%s","short_name":"Kaapana App","icons":[{"src":"icon.png","sizes":"any","type":"image/png"}]}\n' "$APP_TAB_TITLE" > "$DASHBOARD/manifest.json"
    log "dashboard: tab title set to '$APP_TAB_TITLE'"
fi

# clearup
PASSWORD=
HTTP_PASSWORD=

log "startup: handing off to supervisord"
exec /bin/tini -- supervisord -n -c /etc/supervisor/supervisord.conf
