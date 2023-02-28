#!/bin/bash
set -euf -o pipefail

# check if stdout is a terminal
if test -t 1; then

    # see if it supports colors
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

# TODO for offline installation
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

function proxy_environment {
    
    echo "${YELLOW}Checking proxy settings ...${NC}"
    
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

function no_proxy_environment {
    echo "${GREEN}Checking no_proxy settings${NC}"
    if [ ! -v no_proxy ] && [ ! -v NO_PROXY ]; then
        echo "${YELLOW}no_proxy not found, setting it and adding ${HOSTNAME}${NC}"
        echo "NO_PROXY=127.0.0.1,$HOSTNAME,10.1.0.0/16,10.152.183.0/24" >> /etc/environment
        echo "no_proxy=127.0.0.1,$HOSTNAME,10.1.0.0/16,10.152.183.0/24" >> /etc/environment
        sed -i "$ a\\${INSERTLINE}" /etc/environment && echo "Adding $HOSTNAME to no_proxy"
    else
        echo "${YELLOW}no_proxy | NO_PROXY found - check if complete ...!${NC}"

        # remove any " from no_proxy ENV
        no_proxy=$( echo $no_proxy | sed 's/"//g')
        
        if [[ $no_proxy == *"10.152.183.0/24"* ]]; then
            echo "${GREEN}NO_PROXY is already configured correctly ...${NC}"
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

function install_packages_almalinux {
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
        
        echo "${YELLOW}Installing snap, nano, jq and curl${NC}"
        yum install -y snapd nano jq curl
    fi
    
    echo "${YELLOW}Enabling snap${NC}"
    systemctl enable --now snapd.socket

    echo "${YELLOW}Create link ...${NC}"
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

    [[ ":$PATH:" != *":/snap/bin"* ]] && echo "${YELLOW}adding snap path ...${NC}" && source /etc/profile.d/set_path.sh

    if [ -v http_proxy ]; then
        echo "${YELLOW}setting snap proxy ...${NC}"
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
        echo "${YELLOW}Check if apt is locked ...${NC}"
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
            echo -en "\r[$j] Waiting for other software managers to finish ..." 
            sleep 0.5
            ((i=i+1))
        done 

        echo "${YELLOW}APT update & upgrade${NC}"
        apt update
        if [ ! "$QUIET" = "true" ]; then
            apt upgrade -y
        else
            # does not work
            export DEBIAN_FRONTEND=noninteractive
            apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
        fi

        echo "${YELLOW}Installing nano,jq,curl,net-tools ...${NC}"
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
    fi
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
        echo "${YELLOW}Activating GPU ...${NC}"
        microk8s.enable gpu && echo "${GREEN}OK${NC}" || (echo "${YELLOW}Trying with LD_LIBRARY_PATH to activate GPU ...${NC}" && LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+LD_LIBRARY_PATH:}/lib64" microk8s.enable gpu) || (echo "${RED}######################## ERROR WHILE ACTIVATING GPU! ########################${NC}" && exit 1)
        echo "${YELLOW}Waiting for nvidia-device-plugin-daemonset ...${NC}"
    else
        echo "${YELLOW}No GPU support.${NC}"
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

function install_microk8s {
    if command -v microk8s &> /dev/null
    then
        echo ""
        echo "${GREEN}microk8s already installed ...${NC}"
        echo "${GREEN}-> skipping installation ${NC}"
        echo ""
        echo ""
        echo "${GREEN}If you want to start-over use the --uninstall parameter first! ${NC}"
        echo ""
        echo ""
    else
        echo "${YELLOW}microk8s not installed -> start installation ${NC}"
        
        if [ ! -z "$OFFLINE_TAR_PATH" ]; then
            echo "${RED}-> HAS TO BE CHECKED FIRST! ${NC}"
            exit 1

            # echo "${YELLOW} -> offline installation! ${NC}"
            # TAR_LOCATION=$(dirname "$OFFLINE_TAR_PATH")/$(basename "$OFFLINE_TAR_PATH" .tar.gz)
            # export TAR_LOCATION
            # echo $TAR_LOCATION
            # echo Unpacking $OFFLINE_TAR_PATH to $TAR_LOCATION
            # tar -xvf $OFFLINE_TAR_PATH -C  $(dirname "$TAR_LOCATION")
            # set +euf
            # core_digits=$(find $TAR_LOCATION/core* -maxdepth 0 -not -type d -printf "%f\n" | sed -e s/[a-zcore_\/.]//g | head -1)        
            # microk8s_digits=$(find $TAR_LOCATION/microk8s* -maxdepth 0 -not -type d -printf "%f\n" | sed -e s/[a-zmicrok8s_\/.]//g | head -1)  
            # helm_digits=$(find $TAR_LOCATION/helm* -maxdepth 0 -not -type d -printf "%f\n" | sed -e s/[a-zhelm_\/.]//g | head -1)  
            # set -euf
            # echo "${YELLOW}Installing core...${NC}"
            # snap ack $TAR_LOCATION/core_${core_digits}.assert
            # snap install $TAR_LOCATION/core_${core_digits}.snap
            # echo "${YELLOW}Installing microk8s...${NC}"
            # snap ack $TAR_LOCATION/microk8s_${microk8s_digits}.assert
            # snap install --classic  $TAR_LOCATION/microk8s_${microk8s_digits}.snap
            # echo "${YELLOW}Installing Helm...${NC}"
            # snap ack $TAR_LOCATION/helm_${helm_digits}.assert
            # snap install --classic  $TAR_LOCATION/helm_${helm_digits}.snap
            
            # echo "${YELLOW}Wait until microk8s is ready...${NC}"
            # microk8s.status --wait-ready
            # echo Importing Images from $TAR_LOCATION/microk8s_images
            # ls $TAR_LOCATION/microk8s_images | xargs -I {} bash -c 'apply_microk8s_image_import "$@"' _ {}
            # rm -r $TAR_LOCATION
        else
            echo "${YELLOW}Installing microk8s v$DEFAULT_MICRO_VERSION ...${NC}"
            snap install microk8s --classic --channel=$DEFAULT_MICRO_VERSION
            
            echo "${YELLOW}Installing Helm v$DEFAULT_HELM_VERSION ...${NC}"
            snap install helm --classic --channel=$DEFAULT_HELM_VERSION
        fi
        echo "${YELLOW}Stopping microk8s for configuration ...${NC}"
        microk8s.stop

        set +e
        echo "${YELLOW}Enable node_port-range=80-32000 ...${NC}";
        insert_text "--service-node-port-range=80-32000" /var/snap/microk8s/current/args/kube-apiserver
        echo "${YELLOW}Disable insecure port ...${NC}";
        insert_text "--insecure-port=0" /var/snap/microk8s/current/args/kube-apiserver
        
        echo "${YELLOW}Set limit of completed pods to 200 ...${NC}";
        insert_text "--terminated-pod-gc-threshold=200" /var/snap/microk8s/current/args/kube-controller-manager
        set -e

        echo "${YELLOW}Set vm.max_map_count=262144${NC}"
        sysctl -w vm.max_map_count=262144
        sh -c "echo 'vm.max_map_count=262144' >> /etc/sysctl.conf"
        
        echo "${YELLOW}Reload systemct daemon ...${NC}"
        systemctl daemon-reload

        echo "${YELLOW}Set alias for kubectl: $USER_HOME/.bashrc ${NC}"
        set +e
        insert_text "alias kubectl=\"microk8s.kubectl\"" $USER_HOME/.bashrc
        set -e

        echo "${YELLOW}Set auto-completion for kubectl: $USER_HOME/.bashrc ${NC}"
        set +e
        insert_text "# microk8s.kubectl --help > /dev/null 2>&1 && source <(microk8s.kubectl completion bash)" $USER_HOME/.bashrc
        set -e
        
        echo "${YELLOW}Starting microk8s${NC}"
        microk8s.start
        echo "${YELLOW}Wait until microk8s is ready ...${NC}"
        microk8s.status --wait-ready >/dev/null 2>&1
        
        echo "${YELLOW}Enable microk8s RBAC ...${NC}"
        microk8s.enable rbac

        echo "${YELLOW}Enable microk8s DNS ...${NC}"
        microk8s.enable dns:$DNS

        echo "${YELLOW}Waiting for DNS to be ready ...${NC}"
        microk8s.kubectl rollout status -n kube-system deployment coredns --timeout=120s

        echo "${YELLOW}Create dir: $USER_HOME/.kube ...${NC}"
        mkdir -p $USER_HOME/.kube

        echo "${YELLOW}Export Kube-Config to $USER_HOME/.kube/config ...${NC}"
        microk8s.kubectl config view --raw > $USER_HOME/.kube/config
        chmod 600 $USER_HOME/.kube/config

        if [ "$REAL_USER" != "root" ]; then
            echo "${YELLOW} Setting non-root permissions ...${NC}"
            sudo usermod -a -G microk8s $REAL_USER
            sudo chown -f -R $REAL_USER $USER_HOME/.kube
        fi

        # TODO Offline Installation
        # if [ "$PREPARE_OFFLINE_SNAP" = "true" ];then
        #     DUMP_TAR_DIR=snap_offline_microk8s_${DEFAULT_MICRO_VERSION//\//@}_helm_${DEFAULT_HELM_VERSION//\//@}
        #     export DUMP_TAR_DIR
        #     mkdir -p $DUMP_TAR_DIR
        #     mkdir -p $DUMP_TAR_DIR/microk8s_images
        #     enable_gpu
        #     microk8s.ctr images ls | awk {'print $1'} | xargs -I {} bash -c 'apply_microk8s_image_export "$@"' _ {}
        #     snap download core --target-directory $DUMP_TAR_DIR
        #     snap download microk8s  --channel=$DEFAULT_MICRO_VERSION --target-directory $DUMP_TAR_DIR
        #     snap download helm --channel=$DEFAULT_HELM_VERSION --target-directory $DUMP_TAR_DIR
        #     tar -czvf $DUMP_TAR_DIR.tar.gz $DUMP_TAR_DIR
        #     rm -r $DUMP_TAR_DIR
        #     snap remove microk8s
        #     snap remove helm
        #     exit 0
        # fi
        

        echo ""
        echo ""
        echo ""
        
        if [ "$REAL_USER" != "root" ]; then
            echo "${GREEN}           Installation successful.${NC}"
            echo "${GREEN}                 Please run:${NC}"
            echo ""
            echo "${RED}----->           newgrp microk8s           <-----${NC}"
            echo ""
            echo "${GREEN}           or reboot the system${NC}"
            echo ""
        fi
        echo ""
        echo "${YELLOW}Then continue with the platform deployment script.${NC}"
        
        echo ""
        echo ""
        echo ""
    fi
    echo ""
    echo "${GREEN} DONE ${NC}"
    echo ""
}

function install_wazuh_agent {
    architecture=$(uname -m)
    arm="arm"

    # values checked based on: https://wiki.debian.org/ArchitectureSpecificsMemo
    if [ "$architecture" == "x86_64" ]; then
        wazuh_package_url="https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_4.3.9-1_amd64.deb"
    elif [ "$architecture" == "i386" ] || [ "$architecture" == "i486" ] || [ "$architecture" == "i586" ] || [ "$architecture" == "i686" ]; then
        wazuh_package_url="https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_4.3.9-1_i386.deb"
    elif [ "$architecture" == "aarch64" ]; then
        wazuh_package_url="https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_4.3.9-1_arm64.deb"
    elif [[ $architecture == $arm* ]]; then
        wazuh_package_url="https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_4.3.9-1_armhf.deb"
    else
        # no supported architecture found
        return 1
    fi

    curl -so wazuh-agent-4.3.9.deb $wazuh_package_url >/dev/null
    WAZUH_MANAGER='localhost' WAZUH_AGENT_GROUP='default' WAZUH_MANAGER_PORT='1514' WAZUH_REGISTRATION_PORT='1515' dpkg -i ./wazuh-agent-4.3.9.deb >/dev/null 
    
    rm wazuh-agent-4.3.9.deb >/dev/null

    if [ $? -ne 0 ]; then
        return 1
    fi

    systemctl daemon-reload
    systemctl enable wazuh-agent >/dev/null 2>&1 
    if ! systemctl is-enabled wazuh-agent > /dev/null; then
        uninstall_wazuh_agent
        return 1
    fi

    systemctl start wazuh-agent
    if ! systemctl is-active wazuh-agent > /dev/null; then
        uninstall_wazuh_agent
        return 1
    fi

    return 0
}

function uninstall_wazuh_agent {
    # if package is not insalled and service not active, just return
    if ! dpkg -s wazuh_agent &> /dev/null && ! systemctl is-active wazuh_agent > /dev/null; then
        return 0
    fi

    # return false if any of these fail
    apt-get remove --purge wazuh-agent
    if dpkg -s wazuh_agent &> /dev/null; then
        return 1
    fi

    systemctl disable wazuh-agent >/dev/null 2>&1 
    if systemctl is-enabled wazuh-agent > /dev/null; then
        return 1
    fi

    systemctl daemon-reload
    return 0
}

function change_version {
    echo "${YELLOW}Switching to K8s version $DEFAULT_MICRO_VERSION ${NC}"
    snap refresh microk8s --channel $DEFAULT_MICRO_VERSION --classic
}

function uninstall {
    echo ""
    echo "${YELLOW}Uninstalling Helm ...${NC}"
    snap remove helm --purge && echo "${GREEN}DONE${NC}" || echo "${RED}########################  NOT SUCCESSFUL! ########################${NC}"

    echo "${YELLOW}Uninstalling microk8s ...${NC}"
    snap remove microk8s --purge && echo "${GREEN}DONE${NC}" || echo "${RED}########################  NOT SUCCESSFUL! ########################${NC}"

    echo "${YELLOW}Uninstalling Wazuh agent ...${NC}"
    uninstall_wazuh_agent && echo "${GREEN}DONE${NC}" || echo "${RED}########################  NOT SUCCESSFUL! ########################${NC}"
    echo ""
    echo ""
    echo "${YELLOW}UNINSTALLATION DONE ${NC}"
    echo ""
    echo ""

}

OS_PRESENT=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
OS_PRESENT="${OS_PRESENT%\"}"
OS_PRESENT="${OS_PRESENT#\"}"
REAL_USER=${SUDO_USER:-$USER}
if [ -v SUDO_USER ]; then
    USER_HOME=$(getent passwd $SUDO_USER | cut -d: -f6)
else
    USER_HOME=$HOME
fi

if [ "$EUID" -ne 0 ]
then echo -e "Please run the script with root privileges!";
    exit 1
fi
echo ""
echo -e "${GREEN}OS:        $OS_PRESENT ${NC}";
echo -e "${GREEN}REAL_USER: $REAL_USER ${NC}";
echo -e "${GREEN}USER_HOME: $USER_HOME ${NC}";
echo ""

### Parsing command line arguments:
usage="$(basename "$0")

_Flag: -gpu --enable-gpu     will activate gpu support for kubernetes (default: false)
_Flag: -q   --quiet          will activate quiet mode (default: false)
_Flag: -sv  --switch-version will switch the Kubernetes version to [-v version]
_Flag:      --uninstall      removes microk8s and helm from the system

_Argument: -v --version [opt]
where opt is:
    1.22/stable --> for Kubernetes v1.22
    1.23/stable --> for Kubernetes v1.23
    default: 1.23/stable

_Argument: -os --operating-system [opt]
where opt is:
    AlmaLinux --> AlmaLinux
    Ubuntu    --> Ubuntu
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
        
        --install-almalinux-packages)
            install_packages_almalinux
            exit 0
        ;;
        
        --uninstall)
            uninstall
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
    "AlmaLinux")
        echo -e "${GREEN}Starting AlmaLinux installation...${NC}";
        proxy_environment
        install_packages_almalinux
        install_microk8s
    ;;

    "Ubuntu")
        echo -e "${GREEN}Starting Ubuntu installation...${NC}";
        proxy_environment
        install_packages_ubuntu
        install_wazuh_agent
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
        echo "${RED}This script supports: Ubuntu and AlmaLinux${NC}"
        echo -e "$usage"
        exit 1
esac