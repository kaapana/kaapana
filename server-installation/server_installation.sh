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
fi


# DOMAIN=$(hostname -f)
# IPADDRESS=$(hostname -i | grep -Pom 1 '[0-9.]{7,15}')

# if [[ $IPADDRESS =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]] && [[ ! $IPADDRESS == "127.0.0.1" ]]; then
#     echo -e "${GREEN}IP-address: $IPADDRESS - ok!${NC}" ;
#     echo -e "${YELLOW}Please check if this is the correct IP address of the server:${NC}" ;
#     read -e -p "**** IP: " -i "$IPADDRESS" IPADDRESS
# else
#     echo
#     echo -e "${YELLOW}Enter IP-address of the server";
#     read -p "**** IP: ${NC}" IPADDRESS
#     echo -e "IPADRESS: $IPADDRESS";
# fi

# echo -e ""
# echo -e "${YELLOW}Please enter the domain (FQDN) of the server.${NC}" ;
# echo -e "${YELLOW}The suggestion could be incorrect!${NC}" ;
# echo -e "${YELLOW}The IP address should work as well (not recommended - will not work with valid certificates.)${NC}" ;
# read -e -p "**** server domain (FQDN): " -i "$DOMAIN" DOMAIN

# no_proxy_url="NO_PROXY=127.0.0.1,localhost,10.1.0.0/16,10.152.183.0/24,$IPADDRESS,$DOMAIN"


function no_proxy_environment {
    echo "${GREEN}Checking no_proxy settings${NC}"
    if [ ! -v no_proxy ]; then
        echo "${YELLOW}no_proxy not found, setting it and adding ${HOSTNAME}${NC}"
        INSERTLINE="no_proxy=$HOSTNAME"
        sed -i "$ a\\${INSERTLINE}" /etc/environment && echo "Adding $HOSTNAME to no_proxy"
    else
        echo "${YELLOW}no_proxy found, checking of $HOSTNAME is part of it!${NC}"
        echo $no_proxy
        INSERTLINE="no_proxy=$no_proxy,$HOSTNAME"
        grep -q '\bno_proxy\b.*\b'${HOSTNAME}'\b' /etc/environment || sed -i '/no_proxy=/d' /etc/environment
        echo $INSERTLINE
        grep -q '\bno_proxy\b.*\b'${HOSTNAME}'\b' /etc/environment  && echo "$HOSTNAME already part of no_proxy ...." || (sed -i "$ a\\${INSERTLINE}" /etc/environment && echo "Adding $HOSTNAME to no_proxy")
    fi
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
        apt upgrade -y

        apt install -y nano jq curl

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
function install_microk8s {
    
    echo "${YELLOW}Checking /flannel/subnet.env...${NC}"
    
    subnet_path="/var/snap/microk8s/common/run/flannel/subnet.env"
    if [ ! -f "$subnet_path" ]
    then
        echo "${YELLOW}--> Insalling subnet.env...${NC}"
        mkdir -p /var/snap/microk8s/common/run/flannel
        touch $subnet_path
        set +e
        insert_text "FLANNEL_NETWORK=10.1.0.0/16" $subnet_path
        insert_text "FLANNEL_SUBNET=10.1.28.1/24" $subnet_path
        insert_text "FLANNEL_MTU=1450" $subnet_path
        insert_text "FLANNEL_IPMASQ=false" $subnet_path
        set -e

        echo "${GREEN}DONE -> subnet.env:${NC}"
        cat $subnet_path

    else
        echo "${GREEN}--> subnet.env already found!.${NC}"
    fi

    
    echo "${YELLOW}Installing microk8s...${NC}"
    snap install microk8s --classic --channel=$DEFAULT_MICRO_VERSION
    
    echo "${YELLOW}Installing Helm...${NC}"
    snap install helm --classic --channel=$HELM_VERSION
    
    echo "${YELLOW}Wait until microk8s is ready...${NC}"
    microk8s.status --wait-ready
    
    echo "${YELLOW}Enable microk8s DNS...${NC}"
    microk8s.enable dns
    
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
    insert_text "--service-node-port-range=80-32000" /var/snap/microk8s/current/args/kube-apiserver
    set -e
    if [ -v http_proxy ]; then
        echo "${YELLOW}setting containerd proxy...${NC}"
        set +e
        insert_text "HTTP_PROXY=$http_proxy" /var/snap/microk8s/current/args/containerd-env 
        insert_text "HTTPS_PROXY=$https_proxy" /var/snap/microk8s/current/args/containerd-env 
        insert_text "no_proxy=$no_proxy" /var/snap/microk8s/current/args/containerd-env 
        set -e
    else
        echo "No proxy needed..."
    fi
    # set +e
    # echo "${YELLOW}Enable --authentication-token-webhook=true @kubelet ${NC}"
    # insert_text "--authentication-token-webhook=true" /var/snap/microk8s/current/args/kubelet
    
    # echo "${YELLOW}Enable --authorization-mode=Webhook @kubelet ${NC}"
    # insert_text "--authorization-mode=Webhook" /var/snap/microk8s/current/args/kubelet
    # set -e
    
    echo "${YELLOW}Restarting api-server${NC}"
    systemctl restart snap.microk8s.daemon-apiserver
    echo "${YELLOW}Restarting kubelet${NC}"
    systemctl restart snap.microk8s.daemon-kubelet

    echo "${YELLOW}Restarting setting vm.max_map_count=262144${NC}"
	sysctl -w vm.max_map_count=262144
    sh -c "echo 'vm.max_map_count=262144' >> /etc/sysctl.conf"
    
    echo "${YELLOW}Restarting snap.microk8s.daemon-containerd.service ...${NC}"
    systemctl daemon-reload
    systemctl restart snap.microk8s.daemon-containerd.service 
    
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
        
        chown -R $SUDO_USER:$user_group $homedir/.kube
        chown -R $SUDO_USER:$user_group $homedir/.cache
        chown -R $SUDO_USER:$user_group $homedir/snap
    fi

    mkdir -p /root/.kube
    microk8s.kubectl config view --raw > /root/.kube/config
    

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
        # while true; do
        #     read -p "Do you want to install Nvidia drivers?" yn
        #     case $yn in
        #         [Yy]* ) install_nvidia_drivers;break;;
        #         [Nn]* ) break;;
        #         * ) echo "Please answer yes or no.";;
        #     esac
        # done
    else
        GPU_SUPPORT=false;
    fi

    if [ $GPU_SUPPORT == true ];then
        echo "${YELLOW}Activating GPU...${NC}"
        # did not work on Ubuntu: LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/lib64" 
        microk8s.enable gpu && echo "${GREEN}OK${NC}" || (echo "${RED}######################## ERROR WHILE ACTIVATING GPU! ########################${NC}" && exit 1)
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
        microk8s.kubectl delete secret certificate -n kube-system
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
DEFAULT_MICRO_VERSION=1.18/stable
HELM_VERSION=3.1/stable

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
