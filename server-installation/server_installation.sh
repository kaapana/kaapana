#!/bin/bash
set -euf -o pipefail

# check if stdout is a terminal...
if test -t 1; then

    # see if it supports colors...
    ncolors=$(tput colors)

    if test -n "$ncolors" && test $ncolors -ge 8; then
        BOLD="$(tput bold)"
        underline="$(tput smul)"
        standout="$(tput smso)"
        NC="$(tput sgr0)"
        BLACK="$(tput setaf 0)"
        RED="$(tput setaf 1)"
        GREEN="$(tput bold)$(tput setaf 2)"
        YELLOW="$(tput bold)$(tput setaf 3)"
        BLUE="$(tput bold)$(tput setaf 4)"
        MAGENTA="$(tput bold)$(tput setaf 5)"
        CYAN="$(tput bold)$(tput setaf 6)"
        WHITE="$(tput bold)$(tput setaf 7)"
    fi
# else set default empty values
else
    BOLD=""
    underline=""
    standout=""
    NC=""
    BLACK=""
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    MAGENTA=""
    CYAN=""
    WHITE=""
fi

function no_proxy_environment {
    echo "${GREEN}Checking no_proxy settings${NC}"
    if [ ! -v no_proxy ] && [ ! -v NO_PROXY ]; then
        echo "${YELLOW}no_proxy not found, setting it and adding ${HOSTNAME}${NC}"
        echo "NO_PROXY=127.0.0.1,$HOSTNAME,10.1.0.0/16,10.152.183.0/24" >> /etc/environment
        echo "no_proxy=127.0.0.1,$HOSTNAME,10.1.0.0/16,10.152.183.0/24" >> /etc/environment
        sed -i "$ a\\${INSERTLINE}" /etc/environment && echo "Adding $HOSTNAME to no_proxy"
    else
        echo "${YELLOW}no_proxy | NO_PROXY found - check if complete ...!${NC}"

        if [[ $no_proxy == *"10.152.183.0/24"* ]]; then
            echo "${GREEN}NO_PROXY is already configured correctly...${NC}"
            return
        fi

        if grep -Fq "NO_PROXY" /etc/environment
        then
            sed -i "/NO_PROXY/c\NO_PROXY=$no_proxy,10.1.0.0/16,10.152.183.0/24" /etc/environment
        else
            echo "NO_PROXY=127.0.0.1,$HOSTNAME,10.1.0.0/16,10.152.183.0/24" >> /etc/environment
        fi

        if grep -Fq "no_proxy" /etc/environment
        then
            sed -i "/no_proxy/c\no_proxy=$no_proxy,10.1.0.0/16,10.152.183.0/24" /etc/environment
        else
            echo "no_proxy=127.0.0.1,$HOSTNAME,10.1.0.0/16,10.152.183.0/24" >> /etc/environment
        fi
    fi
    echo "${GREEN}Source /etc/environment ${NC}"
    source /etc/environment
}

function proxy_environment {
    
    echo "${YELLOW}Checking proxy settings...${NC}"
    
    if [ ! -v http_proxy ]; then
        echo "${RED}No proxy has been found!${NC}"
        while true; do
            read -p "Is this correct and you don't need a proxy?" yn
                case $yn in
                    [Yy]* ) break;;
                    [Nn]* ) echo "please configure your system proxy (http_proxy + https_proxy -> /etc/environment)" && exit;;
                    * ) echo "Please answer yes or no.";;
                esac
        done
    else
        echo "${GREEN}Proxy ok!${NC}"
        no_proxy_environment
    fi
}


function install_packages_centos {
    echo "${YELLOW}Check packages...${NC}"
    if [ -x "$(command -v snap)" ] && [ -x "$(command -v jq)" ]; then
        echo "${GREEN}Dependencies ok.${NC}"
    else

        echo "${YELLOW}Enable epel-release${NC}"
        yum install -y epel-release
        echo "${YELLOW}YUM update & upgrade${NC}"
        set +e
        yum check-update -y 
        yum clean all -y
        yum update -y
	    yum upgrade -y
        set -e
        
        echo "${YELLOW}Installing snap, nano and jq${NC}"
        yum install -y snapd nano jq curl
    fi
    
    echo "${YELLOW}Enabling snap${NC}"
    systemctl enable --now snapd.socket

    echo "${YELLOW}Create link...${NC}"
    ln -sf /var/lib/snapd/snap /snap

    echo "${YELLOW}Waiting for snap ...${NC}"
    snap wait system seed.loaded
    
    if [ ! -f /etc/profile.d/set_path.sh ]; then
        echo "${YELLOW}Adding /snap/bin to path${NC}"
        INSERTLINE="PATH=\$PATH:/snap/bin"
        echo "$INSERTLINE" > /etc/profile.d/set_path.sh
        chmod +x /etc/profile.d/set_path.sh
        sed -i -r -e '/^\s*Defaults\s+secure_path/ s[=(.*)[=\1:/usr/local/bin:/snap/bin[' /etc/sudoers
    else
        echo "${GREEN}/etc/profile.d/set_path.sh already exists!${NC}"
    fi

    [[ ":$PATH:" != *":/snap/bin"* ]] && echo "${YELLOW}adding snap path...${NC}" && source /etc/profile.d/set_path.sh

    if [ -v http_proxy ]; then
        echo "${YELLOW}setting snap proxy...${NC}"
        snap set system proxy.http="$http_proxy"
        snap set system proxy.https="$http_proxy"
    else
        echo "${GREEN}No snap proxy needed${NC}"
    fi
    

}

function install_packages_ubuntu {
    if [ -x "$(command -v nano)" ] && [ -x "$(command -v jq)" ] && [ -x "$(command -v snap)" ]; then
        echo "${GREEN}Dependencies ok.${NC}"
    else
        echo "${YELLOW}Check if apt is locked...${NC}"
        i=0
        tput sc
        
        while [ fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 ] || [ fuser /var/lib/dpkg/lock >/dev/null 2>&1 ]; do
            case $(($i % 4)) in
                0 ) j="-" ;;
                1 ) j="\\" ;;
                2 ) j="|" ;;
                3 ) j="/" ;;
            esac
            tput rc
            echo -en "\r[$j] Waiting for other software managers to finish..." 
            sleep 0.5
            ((i=i+1))
        done 

        echo "${YELLOW}APT update & upgrade${NC}"
        apt update
        if [ ! "$QUIET" = "true" ]; then
            apt upgrade -y
        else
            export DEBIAN_FRONTEND=noninteractive
            apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
        fi

        apt install -y nano jq curl net-tools

        if [ -x "$(command -v snap)" ]; then
            echo "${GREEN}Snap ok.${NC}"
        else

            echo "${YELLOW}Snap not installed! ${NC}"
            apt install -y snapd
            echo "${YELLOW}Snap has been installed -> reboot needed! ${NC}"
            echo "${YELLOW}Please restart this script afterwards. ${NC}"
            echo "${YELLOW}Please reboot now ${NC}"
            exit 0
        fi

        echo "${YELLOW}Installing JQ${NC}"
    fi
    

    
}

function insert_text {
    search_string=$(echo "$1" | sed "s/--//")
    search_string=$(echo "$search_string" | sed "s/help/--help/")
    insert_string=$1
    filepath=$2
    rc=1

    echo "${YELLOW}Checking $insert_string in $filepath.. ${NC}"
    [ -f $filepath ] || { echo "$filepath does not exist! -> abort." && exit 1; }
    grep -q "$search_string" $filepath && echo "${YELLOW}SKIPPED: $insert_string ....${NC}" || { echo "${GREEN}Setting: $insert_string >> $filepath ${NC}" && rc=0 && sh -c "echo '$insert_string' >> $filepath"; }
    
    return $rc
}

function change_version {
    echo "${YELLOW}Switching to K8s version $DEFAULT_MICRO_VERSION ${NC}"
    snap refresh microk8s --channel $DEFAULT_MICRO_VERSION --classic

}

apply_microk8s_image_export() {
    IMAGE=$1
    if [[ $IMAGE != "REF" ]];
    then
        if [[ $IMAGE != sha* ]];
        then
            echo "${GREEN}Pulling $IMAGE"
            microk8s ctr image pull --all-platforms $IMAGE
        fi
        echo "${GREEN}Exporting $IMAGE"
        microk8s ctr images export $DUMP_TAR_DIR/microk8s_images/${IMAGE//\//@} $IMAGE
    fi
    return 0
}

export -f apply_microk8s_image_export

apply_microk8s_image_import() {
    IMAGE=$1
    BASE_NAME=(${IMAGE//:/ })
    BASE_NAME=${BASE_NAME[0]}
    echo Uploading $IMAGE
    
    microk8s ctr images import --base-name ${BASE_NAME//@/\/} $TAR_LOCATION/microk8s_images/$IMAGE
}

export -f apply_microk8s_image_import


function install_microk8s {
    
    
    if [ ! -z "$OFFLINE_TAR_PATH" ]; then
        TAR_LOCATION=$(dirname "$OFFLINE_TAR_PATH")/$(basename "$OFFLINE_TAR_PATH" .tar.gz)
        export TAR_LOCATION
        echo $TAR_LOCATION
        echo Unpacking $OFFLINE_TAR_PATH to $TAR_LOCATION
        tar -xvf $OFFLINE_TAR_PATH -C  $(dirname "$TAR_LOCATION")
        set +euf
        core_digits=$(find $TAR_LOCATION/core* -maxdepth 0 -not -type d -printf "%f\n" | sed -e s/[a-zcore_\/.]//g | head -1)        
        microk8s_digits=$(find $TAR_LOCATION/microk8s* -maxdepth 0 -not -type d -printf "%f\n" | sed -e s/[a-zmicrok8s_\/.]//g | head -1)  
        helm_digits=$(find $TAR_LOCATION/helm* -maxdepth 0 -not -type d -printf "%f\n" | sed -e s/[a-zhelm_\/.]//g | head -1)  
        set -euf
        echo "${YELLOW}Installing core...${NC}"
        snap ack $TAR_LOCATION/core_${core_digits}.assert
        snap install $TAR_LOCATION/core_${core_digits}.snap
        echo "${YELLOW}Installing microk8s...${NC}"
        snap ack $TAR_LOCATION/microk8s_${microk8s_digits}.assert
        snap install --classic  $TAR_LOCATION/microk8s_${microk8s_digits}.snap
        echo "${YELLOW}Installing Helm...${NC}"
        snap ack $TAR_LOCATION/helm_${helm_digits}.assert
        snap install --classic  $TAR_LOCATION/helm_${helm_digits}.snap
        
        echo "${YELLOW}Wait until microk8s is ready...${NC}"
        microk8s.status --wait-ready
        echo Importing Images from $TAR_LOCATION/microk8s_images
        ls $TAR_LOCATION/microk8s_images | xargs -I {} bash -c 'apply_microk8s_image_import "$@"' _ {}
        rm -r $TAR_LOCATION
    else
        echo "${YELLOW}Installing microk8s...${NC}"
        snap install microk8s --classic --channel=$DEFAULT_MICRO_VERSION
        
        echo "${YELLOW}Installing Helm...${NC}"
        snap install helm --classic --channel=$DEFAULT_HELM_VERSION
    fi

    echo "${YELLOW}Wait until microk8s is ready...${NC}"
    microk8s.status --wait-ready
    
    echo "${YELLOW}Enable microk8s DNS...${NC}"
    microk8s.enable dns:$DNS

    echo "${YELLOW}Waiting for dns...${NC}"
    microk8s.kubectl rollout status -n kube-system deployment coredns --timeout=120s

    if [ "$PREPARE_OFFLINE_SNAP" = "true" ];then
        DUMP_TAR_DIR=snap_offline_microk8s_${DEFAULT_MICRO_VERSION//\//@}_helm_${DEFAULT_HELM_VERSION//\//@}
        export DUMP_TAR_DIR
        mkdir -p $DUMP_TAR_DIR
        mkdir -p $DUMP_TAR_DIR/microk8s_images
        enable_gpu
        microk8s.ctr images ls | awk {'print $1'} | xargs -I {} bash -c 'apply_microk8s_image_export "$@"' _ {}
        snap download core --target-directory $DUMP_TAR_DIR
        snap download microk8s  --channel=$DEFAULT_MICRO_VERSION --target-directory $DUMP_TAR_DIR
        snap download helm --channel=$DEFAULT_HELM_VERSION --target-directory $DUMP_TAR_DIR
        tar -czvf $DUMP_TAR_DIR.tar.gz $DUMP_TAR_DIR
        rm -r $DUMP_TAR_DIR
        snap remove microk8s
        snap remove helm
        exit 0
    fi
    
    echo "${YELLOW} Stopping microk8s for configuration ...${NC}"
    microk8s.stop
    if [ -v SUDO_USER ]; then
        homedir=$(getent passwd $SUDO_USER | cut -d: -f6)
        echo "${YELLOW}Add snap bins to PATH...${NC}"
        INSERTLINE="PATH=$PATH:$homedir/.local/bin:/snap/bin"
        grep -q "$INSERTLINE" /etc/environment || sed -i '/PATH=/d' /etc/environment
        set +e
        insert_text $INSERTLINE /etc/environment
        set -e
    fi
    
    set +e
    echo "Enable port-range=80-32000";
    insert_text "--service-node-port-range=80-32000" /var/snap/microk8s/current/args/kube-apiserver
    insert_text "--insecure-port=0" /var/snap/microk8s/current/args/kube-apiserver
    
    echo "Set limit of completed pods to 200";
    insert_text "--terminated-pod-gc-threshold=200" /var/snap/microk8s/current/args/kube-controller-manager
    set -e
    if [ -v http_proxy ]; then
        echo "${YELLOW}setting containerd proxy...${NC}"
        set +e
        insert_text "HTTP_PROXY=$http_proxy" /var/snap/microk8s/current/args/containerd-env 
        insert_text "HTTPS_PROXY=$https_proxy" /var/snap/microk8s/current/args/containerd-env 
        set -e
    else
        echo "No proxy needed..."
    fi

    if [ -v no_proxy ] || [ -v NO_PROXY ]; then
        echo "${YELLOW}setting containerd no_proxy...${NC}"
        set +e

        if [ -v no_proxy ]; then
            insert_text "no_proxy=$no_proxy" /var/snap/microk8s/current/args/containerd-env 
        elif [ -v NO_PROXY ]; then
            insert_text "no_proxy=$NO_PROXY" /var/snap/microk8s/current/args/containerd-env 
        fi
        set -e
    else
        echo "No_proxy proxy not needed..."
    fi
       
    # echo "${YELLOW}Restarting api-server${NC}"
    # systemctl restart snap.microk8s.daemon-apiserver
    # echo "${YELLOW}Restarting kubelet${NC}"
    # systemctl restart snap.microk8s.daemon-kubelet

    echo "${YELLOW}Restarting setting vm.max_map_count=262144${NC}"
	sysctl -w vm.max_map_count=262144
    sh -c "echo 'vm.max_map_count=262144' >> /etc/sysctl.conf"
    
    echo "${YELLOW}Restarting snap.microk8s.daemon-containerd.service ...${NC}"
    systemctl daemon-reload
    # systemctl restart snap.microk8s.daemon-containerd.service 
    
    if [ -v SUDO_USER ]; then
        homedir=$(getent passwd $SUDO_USER | cut -d: -f6)
        echo "${YELLOW}Set alias kubectl user${NC}"
        set +e
        insert_text "alias kubectl=\"microk8s.kubectl\"" $homedir/.bashrc
        
        echo "${YELLOW}Set auto-completion kubectl user${NC}"
        insert_text "microk8s.kubectl --help > /dev/null 2>&1 && source <(microk8s.kubectl completion bash)" $homedir/.bashrc
        set -e
    fi

    echo "${YELLOW}Set alias kubectl root${NC}"
    set +e
    insert_text "alias kubectl=\"microk8s.kubectl\"" /root/.bashrc
    set -e

    echo "${YELLOW}Set auto-completion kubectl root${NC}"
    set +e
    insert_text "microk8s.kubectl --help > /dev/null 2>&1 && source <(microk8s.kubectl completion bash)" /root/.bashrc
    set -e
    
    echo "${YELLOW}starting microk8s${NC}"
    microk8s.start

    
    if [ -v SUDO_USER ]; then
        homedir=$(getent passwd $SUDO_USER | cut -d: -f6)
        user_group=$(id -g -n $SUDO_USER | cut -d' ' -f 1)
        user_group=$(id -g  $SUDO_USER)

        echo "${YELLOW}Setting usermod${NC}"
        usermod -a -G microk8s $SUDO_USER
        
        echo "${YELLOW}Source bashrc${NC}"
        set +euf
        source $homedir/.bashrc
        set -euf
        
        echo "${YELLOW}Set kubeconfig${NC}"
        mkdir -p $homedir/.kube
        mkdir -p $homedir/.cache
        mkdir -p $homedir/snap
        microk8s.kubectl config view --raw > $homedir/.kube/config

        echo "${YELLOW}Chown $homedir/.kube${NC}"
        echo "${YELLOW}Chown $homedir/.cache${NC}"
        echo "${YELLOW}Chown $homedir/snap${NC}"

        chmod 600 $homedir/.kube/config
        chown -R $SUDO_USER:$user_group $homedir/.kube
        chown -R $SUDO_USER:$user_group $homedir/.cache
        chown -R $SUDO_USER:$user_group $homedir/snap
    fi

    mkdir -p /root/.kube
    microk8s.kubectl config view --raw > /root/.kube/config
    chmod 600 $HOME/.kube/config

    echo ""
    echo ""
    echo ""
    
    echo "${GREEN}           Installation successful.${NC}"
    echo "${GREEN}          Please reboot your system${NC}"
    echo "${YELLOW}Then continue with the platform deployment script.${NC}"
    
    echo ""
    echo ""
    echo ""
}

function enable_gpu {
    if [ ! "$QUIET" = "true" ];then
        while true; do
            read -p "Do you want to enable GPU support (Only if Nvidia GPU is installed)?" yn
            case $yn in
                [Yy]* ) GPU_SUPPORT=true;break;;
                [Nn]* ) GPU_SUPPORT=false;break;;
                * ) echo "Please answer yes or no.";;
            esac
        done
    else
        GPU_SUPPORT=false;
    fi

    if [ $GPU_SUPPORT == true ];then
        echo "${YELLOW}Activating GPU...${NC}"
        microk8s.enable gpu && echo "${GREEN}OK${NC}" || (echo "${YELLOW}Trying with LD_LIBRARY_PATH to activate GPU...${NC}" && LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+LD_LIBRARY_PATH:}/lib64" microk8s.enable gpu) || (echo "${RED}######################## ERROR WHILE ACTIVATING GPU! ########################${NC}" && exit 1)
        echo "${YELLOW}Waiting for nvidia-device-plugin-daemonset...${NC}"
        microk8s.kubectl rollout status -n kube-system daemonset nvidia-device-plugin-daemonset --timeout=120s
    else
        echo "${YELLOW}No GPU support.${NC}"
    fi
}

function install_nvidia_drivers {
    DRIVER_VERISION="NVIDIA-Linux-x86_64-450.57.run"
    echo -e "Starting install_nvidia_drivers: $DRIVER_VERISION ..."

    # Maybe this will not be needed anymore (driver-install flags) -> testing needed

    # created=0
    # blacklist_filepath="/etc/modprobe.d/blacklist-nvidia-nouveau.conf"
    # [ -f $blacklist_filepath ] || { echo "$blacklist_filepath does not exist! -> create file." && created=1 && touch $blacklist_filepath; }

    # set +e
    # insert_text "blacklist nouveau" /etc/modprobe.d/blacklist-nvidia-nouveau.conf
    # insert_text "options nouveau modeset=0" /etc/modprobe.d/blacklist-nvidia-nouveau.conf
    # set -e
    
    # if [ $created -eq 1 ]; then
    #     echo -e "${YELLOW}Nouveau was disabled -> reboot needed!${NC}"
    #     echo -e "${YELLOW}Please restart this script afterwards!${NC}"
    #     exit 0
    # else
    #     echo -e "${GREEN}Nouveau already disabled -> continue${NC}"
    # fi

    if ! lshw -numeric -C display | grep -q 'driver=nvidia' ;then
        echo -e "Installing Nvidia drivers..."  > /dev/stderr;

        [ -f ./$DRIVER_VERISION ] || { echo "Downloading driver..." && curl http://de.download.nvidia.com/XFree86/Linux-x86_64/450.57/$DRIVER_VERISION --output $DRIVER_VERISION; }
        
        chmod +x $DRIVER_VERISION
        ./$DRIVER_VERISION --ui=none --no-questions --accept-license --disable-nouveau --install-libglvnd 
        # ./$DRIVER_VERISION --accept-license --silent
        if [ $? -ne 0 ]; then
            echo -e "${RED}Nvidia drivers could not be installed.${NC}" > /dev/stderr;
            echo -e "${RED}Please check the output and try again. ${NC}" > /dev/stderr;
            exit 1
        else
            echo -e "${GREEN}NVIDIA drivers installed successfully!${NC}"
        fi
    else
        echo -e "${YELLOW}Nvidia drivers already installed!${NC}"  > /dev/stderr;
    fi
}

function install_certs {
    echo -e "Checking if Kubectl is installed..."
    command -v microk8s.kubectl >/dev/null 2>&1 || {
    echo -e >&2 "${RED}Kubectl has to be installed for this script - but it's not installed.  Aborting.${NC}";
    exit 1; }
    echo -e "${GREEN}OK!${NC}"


    echo -e "Checking if correct Kubectl config is in place..."
    microk8s.kubectl get pods --all-namespaces
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Server connection - OK!${NC}"
    else
        echo -e "${RED}Kubectl could not communicate with the server.${NC}"
        echo -e "${RED}Have a look at the output, ${NC}"
        echo -e "${RED}Check if the correct server certificate file is in place @ ~/.kube/config, ${NC}"
        echo -e "${RED}Check if the IP address in the certificate matches the IP address of the server ${NC}"
        echo -e "${RED}and try again.${NC}"
        exit 1
    fi

    if [ ! -f ./tls.key ] || [ ! -f ./tls.crt ]; then
        echo -e "${RED}tls.key or tls.crt could not been found in this directory.${NC}"
        echo -e "${RED}Please rename and copy the files first!${NC}"
        exit 1
    else
        echo -e "files found!"
        echo -e "Creating cluster secret ..."
        microk8s.kubectl delete secret certificate -n kube-system || true
        microk8s.kubectl create secret tls certificate --namespace kube-system --key ./tls.key --cert ./tls.crt
        gatekeeper_pod=$(microk8s.kubectl get pods -n kube-system |grep louketo  | awk '{print $1;}')
        echo "gatekeeper pod: $gatekeeper_pod"
        microk8s.kubectl -n kube-system delete pod $gatekeeper_pod
    fi

    echo -e "${GREEN}DONE${NC}"
}


OS_PRESENT=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
OS_PRESENT="${OS_PRESENT%\"}"
OS_PRESENT="${OS_PRESENT#\"}"

if [ "$EUID" -ne 0 ]
then echo -e "Please run the script with root privileges!";
    exit
else
    echo -e "${YELLOW}ROOT OK ${NC}";
    echo -e "${YELLOW}OS:   $OS_PRESENT ${NC}";
    if [ -v SUDO_USER ]; then
    echo -e "${YELLOW}USER: $SUDO_USER ${NC}";
    fi
    echo ""
fi


### Parsing command line arguments:
usage="$(basename "$0")

_Flag: -gpu --enable-gpu     will activate gpu support for kubernetes (default: false)
_Flag: -q   --quiet          will activate quiet mode (default: false)
_Flag:      --install-certs  set new HTTPS-certificates for the platform
_Flag: -sv  --switch-version will switch the Kubernetes version to [-v version]

_Argument: -v --version [opt]
where opt is:
    1.14/stable --> for Kubernetes v1.14
    1.17/stable --> for Kubernetes v1.17
    1.18/stable --> for Kubernetes v1.18
    1.19/stable --> for Kubernetes v1.19
    default: 1.18/stable

_Argument: -os --operating-system [opt]
where opt is:
    CentOS Linux --> Centos
    Ubuntu       --> Ubuntu
    default: $OS_PRESENT"

QUIET=NA
PREPARE_OFFLINE_SNAP=NA
OFFLINE_TAR_PATH=""
DEFAULT_MICRO_VERSION=1.23/stable
DEFAULT_HELM_VERSION=3.7/stable
DNS="8.8.8.8,8.8.4.4"

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in

        -h|--help)
            echo -e "${YELLOW}$usage ${NC}";
            exit 0
        ;;

        -gpu|--enable-gpu)
            echo -e "${GREEN}Enabling GPU support... ${NC}";
            OS_PRESENT="GPUSUPPORT"
            shift # past argument
        ;;

        -os|--operating-system)
            OS_PRESENT="$2"
            echo -e "${GREEN}OS set to: $OS_PRESENT ${NC}";
            shift # past argument
            shift # past value
        ;;

        -v|--version)
            DEFAULT_MICRO_VERSION="$2"
            echo -e "${GREEN}Kubernetes version set to: $DEFAULT_MICRO_VERSION ${NC}";
            shift # past argument
            shift # past value
        ;;

        -q|--quiet)
            echo -e "${GREEN}QUIET-MODE activated!${NC}";
            QUIET=true
            shift # past argument
        ;;

        -sv|--switch-version)
            OS_PRESENT="SWITCHVERSION"
            shift # past argument
        ;;
        
        --offline-tar-path)
            OFFLINE_TAR_PATH="$2"
            echo -e "${GREEN}SET OFFLINE_TAR_PATH: $OFFLINE_TAR_PATH !${NC}";
            shift # past argument
            shift # past value
        ;;

        --prepare-offline-snap)
            PREPARE_OFFLINE_SNAP=true
            echo -e "${GREEN}SET PREPARE_OFFLINE_SNAP: $PREPARE_OFFLINE_SNAP !${NC}";
            shift # past argument
        ;;

        --install-ubuntu-packages)
            install_packages_ubuntu
            exit 0
        ;;
        
        --install-centos-packages)
            install_packages_centos
            exit 0
        ;;


        --install-certs)
            install_certs
            exit 0
        ;;

        *)    # unknown option
            echo -e "${RED}UNKNOWN ARGUMENT: $key!${NC}";
            echo -e "$usage";
            exit 1
        ;;
    esac
done


case "$OS_PRESENT" in
    "CentOS Linux")
        echo -e "${GREEN}Starting CentOs installation...${NC}";
        proxy_environment
        install_packages_centos
        install_microk8s
    ;;

    "Ubuntu")
        echo -e "${GREEN}Starting Ubuntu installation...${NC}";
        proxy_environment
        install_packages_ubuntu
        install_microk8s
    ;;

    "SWITCHVERSION")
    change_version
        
    ;;

    "GPUSUPPORT")
        enable_gpu
    ;;

    *)  
        echo "${RED}Your OS: $OS_PRESENT is not supported at the moment.${NC}"
        echo "${RED}This scripts suppors: Ubuntu and CentOS Linux${NC}"
        echo -e "$usage"
        exit 1
esac
