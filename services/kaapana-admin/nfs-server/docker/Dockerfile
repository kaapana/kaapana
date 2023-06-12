# Use Alpine 3.17.2 as the base image
FROM docker.io/alpine:3.17.2

# Update packages and install necessary dependencies
RUN apk update && \
    apk add --no-cache \
    nfs-utils \
    rpcbind \
    bash

# Create the directory to be shared via NFS
RUN mkdir -p /nfs_share

# Set permissions for the shared directory
RUN addgroup -g 1000 nfsgroup && \
    adduser -u 1000 -G nfsgroup -D nfsuser && \
    chown -R nfsuser:nfsgroup /nfs_share && \
    chmod 770 /nfs_share


# Add the NFS configuration to /etc/exports
RUN echo '/nfs_share *(rw,sync,no_subtree_check,no_root_squash,insecure)' >> /etc/exports

# Expose NFS ports
EXPOSE 2049/tcp 2049/udp 111/tcp 111/udp

# Add a script to start NFS services
COPY files/start-nfs.sh /start-nfs.sh
RUN chmod +x /start-nfs.sh

# Execute the NFS server startup script
CMD ["/start-nfs.sh"]

LABEL IMAGE="volume-nfs"
LABEL VERSION="0.8"
LABEL CI_IGNORE="False"
