FROM local-only/base-python-gpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-podman"
LABEL VERSION="latest"

ENV HELM_VERSION="v3.8.1"

# Install podman (Ubuntu 20.04)
RUN apt-get update -y \
    && apt-get install curl wget gnupg2 -y \
    && source /etc/os-release \
    && sh -c "echo 'deb http://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /' > /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list" \
    && wget -nv https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable/xUbuntu_${VERSION_ID}/Release.key -O- | apt-key add -  \
    && apt-get update -qq -y \
    && apt-get -qq --yes install podman fuse-overlayfs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create podman user
RUN useradd podman; \
echo podman:10000:5000 > /etc/subuid; \
echo podman:10000:5000 > /etc/subgid;

# Rootfull Podman container storage
RUN mkdir -p /var/lib/containers
# Rootless Podman container storage
RUN mkdir -p /home/podman/.local/share/containers

# Create podman user home directory and set permissions
RUN chown podman:podman -R /home/podman

# Create podman config
COPY files/containers.conf /etc/containers/containers.conf
COPY files/podman-containers.conf /home/podman/.config/containers/containers.conf

# chmod containers.conf and adjust storage.conf to enable Fuse storage.
RUN chmod 644 /etc/containers/containers.conf; sed -i -e 's|^#mount_program|mount_program|g' -e '/additionalimage.*/a "/var/lib/shared",' -e 's|^mountopt[[:space:]]*=.*$|mountopt = "nodev,fsync=0"|g' /etc/containers/storage.conf
RUN mkdir -p /var/lib/shared/overlay-images /var/lib/shared/overlay-layers /var/lib/shared/vfs-images /var/lib/shared/vfs-layers; touch /var/lib/shared/overlay-images/images.lock; touch /var/lib/shared/overlay-layers/layers.lock; touch /var/lib/shared/vfs-images/images.lock; touch /var/lib/shared/vfs-layers/layers.lock

ENV _CONTAINERS_USERNS_CONFIGURED=""
ENV CONTAINERD_SOCK="/root/containerd.sock"

# Install helm
RUN curl https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz | tar -xzO linux-amd64/helm > /usr/local/bin/helm && chmod +x /usr/local/bin/helm
RUN chmod g+rwx /root && mkdir /config && chmod g+rwx /config    
RUN helm plugin install https://github.com/instrumenta/helm-kubeval

WORKDIR /kaapana/app

# Install containerd
RUN curl -L https://github.com/containerd/containerd/releases/download/v1.5.13/containerd-1.5.13-linux-amd64.tar.gz -o containerd.tar.gz
RUN tar -xf containerd.tar.gz
RUN cp bin/ctr /usr/local/bin/ctr && chmod +x /usr/local/bin/ctr
RUN rm -rf containerd* bin/