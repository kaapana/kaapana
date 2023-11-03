FROM docker.io/busybox:1.36

LABEL IMAGE="nfs-init"
LABEL VERSION="1.36"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app
COPY files/init.sh /kaapana/app/init.sh
RUN chmod +x /kaapana/app/init.sh

CMD ["sh","/kaapana/app/init.sh"]
