kaapana() {
    FILEPATH=${2:-.}  
    TAG=$1 
    echo Pushing $TAG of file $FILEPATH to microk8s registry
    podman build -t $TAG -f $FILEPATH
    podman save $TAG -o $TAG.tar
    ctr --namespace k8s.io -address=/root/containerd.sock image import $TAG.tar
    rm -rf $TAG.tar
}