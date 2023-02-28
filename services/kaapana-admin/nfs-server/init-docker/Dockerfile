FROM busybox:1.31

LABEL IMAGE="nfs-init"
LABEL VERSION="1.31"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
COPY files/init.sh /kaapana/app/init.sh
RUN chmod +x /kaapana/app/init.sh

CMD ["sh","/kaapana/app/init.sh"]
