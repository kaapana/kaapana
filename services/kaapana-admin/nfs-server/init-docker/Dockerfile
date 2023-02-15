FROM busybox:1.31

LABEL IMAGE="nfs-init"
LABEL VERSION="1.31"
LABEL CI_IGNORE="False"

WORKDIR /app
COPY files/init.sh /app/init.sh
RUN chmod +x /app/init.sh

CMD ["sh","/app/init.sh"]
