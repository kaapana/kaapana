#!/bin/bash

log() { echo "[base-desktop $(date -u +%H:%M:%S)] $*"; }

log "startup: begin"

if [ -n "$VNC_PASSWORD" ]; then
    echo -n "$VNC_PASSWORD" > /.password1
    x11vnc -storepasswd $(cat /.password1) /.password2
    chmod 400 /.password*
    sed -i 's/^command=x11vnc.*/& -rfbauth \/.password2/' /etc/supervisor/conf.d/supervisord.conf
    export VNC_PASSWORD=
    log "vnc: password authentication enabled"
fi

if [ -n "$X11VNC_ARGS" ]; then
    sed -i "s/^command=x11vnc.*/& ${X11VNC_ARGS}/" /etc/supervisor/conf.d/supervisord.conf
fi

if [ -n "$OPENBOX_ARGS" ]; then
    sed -i "s#^command=/usr/bin/openbox\$#& ${OPENBOX_ARGS}#" /etc/supervisor/conf.d/supervisord.conf
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

# clearup
PASSWORD=
HTTP_PASSWORD=

log "startup: handing off to supervisord"
exec /bin/tini -- supervisord -n -c /etc/supervisor/supervisord.conf
