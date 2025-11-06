#!/bin/bash
# WARNING: This script is deprecated and will be removed in the next Kaapana release.
# Please migrate to `./kaapanactl install`, which supports the same options.
set -euf -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

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

echo "${YELLOW:-}${BOLD:-}WARNING:${NC:-} server_installation.sh is deprecated and will be removed in the next Kaapana release."
echo "${YELLOW:-}${BOLD:-}Please use './kaapanactl install' instead; it accepts the same options as this script.${NC:-}"

function proxy_environment {
    echo "${YELLOW}Checking proxy settings ...${NC}"
    if [ ! "$QUIET" = "true" ];then
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
    else
        echo "QUIET = true";
    fi
}


function no_proxy_environment {
    # Note: This script makes sure no_proxy configuration is configured correctly so microk8s doesn't send cluster traffic to the 
    #       proxy server. The specific settings for ip ranges used by microk8s to request external resource might change in the future
    #       and are (currently) described here: https://microk8s.io/docs/install-proxy
    echo "${GREEN}Checking no_proxy settings${NC}"
    if [ ! -v no_proxy ] && [ ! -v NO_PROXY ]; then
        echo "${YELLOW}no_proxy not found, setting it and adding ${HOSTNAME}${NC}"
        echo "NO_PROXY=127.0.0.1,$HOSTNAME,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" >> /etc/environment
        echo "no_proxy=127.0.0.1,$HOSTNAME,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" >> /etc/environment
        sed -i "$ a\\${INSERTLINE}" /etc/environment && echo "Adding $HOSTNAME to no_proxy"
    else
        echo "${YELLOW}no_proxy | NO_PROXY found - check if complete ...!${NC}"

        if [ -v no_proxy ]; then
                no_proxy=$no_proxy
        else
                no_proxy=$NO_PROXY
        fi

        # remove any " from no_proxy ENV
        no_proxy=$( echo $no_proxy | sed 's/"//g')
        
        if [[ $no_proxy == *"172.16.0.0/16"* ]]; then
            echo "${GREEN}NO_PROXY is already configured correctly ...${NC}"
            return
        fi

        if grep -Fq "NO_PROXY" /etc/environment
        then
            sed -i "/NO_PROXY/c\NO_PROXY=$no_proxy,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" /etc/environment
        else
            echo "NO_PROXY=127.0.0.1,$HOSTNAME,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" >> /etc/environment
        fi

        if grep -Fq "no_proxy" /etc/environment
        then
            sed -i "/no_proxy/c\no_proxy=$no_proxy,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" /etc/environment
        else
            echo "no_proxy=127.0.0.1,$HOSTNAME,10.0.0.0/8,192.168.0.0/16,172.16.0.0/16" >> /etc/environment
        fi
    fi
    echo "${GREEN}Source /etc/environment ${NC}"
    source /etc/environment
}

function install_packages_almalinux {
    echo "${YELLOW}Check packages...${NC}"
    if [ -x "$(command -v snap)" ] && [ -x "$(command -v jq)" ]; then
        echo "${GREEN}Snap installed.${NC}"
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
        echo "${GREEN}snap,nano and jq already installed.${NC}"
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


function install_core {
    local package_name=$1
    echo "${YELLOW}Checking if ${package_name} is installed ... ${NC}"
    if ls -l /var/lib/snapd/snaps | grep ${package_name} ;
    then
        echo ""
        echo "${GREEN}${package_name} is already installed ...${NC}"
        echo "${GREEN}-> skipping installation ${NC}"
        echo ""
    else
        echo "${YELLOW}${package_name} is not installed -> start installation ${NC}"
        if [ "$OFFLINE_SNAPS" = "true" ]; then
            echo "${YELLOW} -> ${package_name} offline installation! ${NC}"
            snap_path=$SCRIPT_DIR/${package_name}.snap
            assert_path=$SCRIPT_DIR/${package_name}.assert
            [ -f $snap_path ] && echo "${GREEN}$snap_path exists ... ${NC}" || (echo "${RED}$snap_path does not exist -> exit ${NC}" && exit 1)
            [ -f $assert_path ] && echo "${GREEN}$assert_path exists ... ${NC}" || (echo "${RED}$assert_path does not exist -> exit ${NC}" && exit 1)
            snap ack $assert_path
            snap install --classic $snap_path
        else
            echo "${YELLOW}${package_name} will be automatically installed ...${NC}"
        fi
    fi
}


function install_helm {
    if command -v helm &> /dev/null
    then
        echo ""
        echo "${GREEN}Helm is already installed ...${NC}"
        echo "${GREEN}-> skipping installation ${NC}"
        echo ""
    else
        echo "${YELLOW}Helm is not installed -> start installation ${NC}"
        if [ "$OFFLINE_SNAPS" = "true" ];then
            echo "${YELLOW} -> Helm offline installation! ${NC}"
            snap_path=$SCRIPT_DIR/helm.snap
            assert_path=$SCRIPT_DIR/helm.assert
            [ -f $snap_path ] && echo "${GREEN}$snap_path exists ... ${NC}" || (echo "${RED}$snap_path does not exist -> exit ${NC}" && exit 1)
            [ -f $assert_path ] && echo "${GREEN}$assert_path exists ... ${NC}" || (echo "${RED}$assert_path does not exist -> exit ${NC}" && exit 1)
            snap ack $assert_path
            snap install --classic $snap_path
        else
            echo "${YELLOW}Installing Helm v$DEFAULT_HELM_VERSION ...${NC}"
            snap install helm --classic --channel=$DEFAULT_HELM_VERSION
        fi
    fi
}

function dns_check {
    if [ ! -z "$DNS" ]; then
        echo "${GREEN}${NC}"
        echo "${GREEN}DNS has been manually configured to '$DNS' ...${NC}"
        echo "${GREEN}${NC}"
    else
        if [ "$OFFLINE_SNAPS" != "true" ];then
            echo "${GREEN}Checking server DNS settings ...${NC}"
            if command -v nslookup dkfz.de &> /dev/null
            then
                echo "${GREEN}DNS lookup was successful ...${NC}"
            else
                echo ""
                echo "${RED}DNS lookup failed -> please check your servers DNS configuration ...${NC}"
                echo "${RED}You can test it with: 'nslookup dkfz.de'${NC}"
                echo ""
                exit 1
            fi
        fi

        set +e
        echo "${GREEN}Get DNS settings nmcli ...${NC}"
        DNS=$(( nmcli dev list || nmcli dev show ) 2>/dev/null | grep DNS |awk -F ' ' '{print $2}' | tr '\ ' ',' | sed 's/,$/\n/')
        
        if [ -z "$DNS" ]; then
            echo "${YELLOW} Trying resolvectl ...${NC}"
            DNS=$(resolvectl status |grep 'DNS Servers' | awk -F ': ' '{print $2}' | tr '\ ' ',' | sed 's/,$/\n/')
        fi

        if [ -z "$DNS" ]; then
            echo "${YELLOW} Trying systemd-resolve...${NC}"
            DNS=$(systemd-resolve --status |grep 'DNS Servers' | awk -F ': ' '{print $2}' | tr '\ ' ',' | sed 's/,$/\n/')
        fi

        if [ -z "$DNS" ]; then
            if [ "$OFFLINE_SNAPS" = "true" ]; then
                echo "${YELLOW}No DNS found, setting fallback DNS...${NC}"
                DNS="8.8.8.8,8.8.4.4"
            else
                echo "${RED}DNS lookup failed.${NC}"
                exit 1
            fi
        fi
                    
        ## Format DNS to be a comma separated list of IP addresses without spaces and newlines
        DNS=$(echo -e $DNS | tr -s ' \n,' ',' | sed 's/,$/\n/')
        echo "${YELLOW}Identified DNS: $DNS ${NC}"

        set -e
    fi
}

function install_microk8s {
    if command -v microk8s &> /dev/null
    then
        echo ""
        echo "${GREEN}microk8s is already installed ...${NC}"
        echo "${GREEN}-> skipping installation ${NC}"
        echo ""
        echo ""
        echo "${GREEN}If you want to start-over use the --uninstall parameter first! ${NC}"
        echo ""
        echo ""
        exit 0
    else
        echo "${YELLOW}microk8s is not installed -> start installation ${NC}"
        dns_check
        
        if [ "$OFFLINE_SNAPS" = "true" ];then
            echo "${YELLOW} -> offline installation! ${NC}"

            echo "${YELLOW}Installing microk8s...${NC}"
            snap_path=$SCRIPT_DIR/microk8s.snap
            assert_path=$SCRIPT_DIR/microk8s.assert
            [ -f $snap_path ] && echo "${GREEN}$snap_path exists ... ${NC}" || (echo "${RED}$snap_path does not exist -> exit ${NC}" && exit 1)
            [ -f $assert_path ] && echo "${GREEN}$assert_path exists ... ${NC}" || (echo "${RED}$assert_path does not exist -> exit ${NC}" && exit 1)
            
            snap ack $assert_path
            snap install --classic $snap_path
            MICROK8S_BASE_IMAGES_TAR_PATH="$SCRIPT_DIR/microk8s_base_images.tar"
            echo "${YELLOW}Start Microk8s image import from $MICROK8S_BASE_IMAGES_TAR_PATH ... ${NC}"
            [ -f $MICROK8S_BASE_IMAGES_TAR_PATH ] && echo "${GREEN}MICROK8S_BASE_IMAGES_TAR exists ... ${NC}" || (echo "${RED}Images tar does not exist -> exit ${NC}" && exit 1)
            echo "${RED}This can take a long time! -> please be patient and wait. ${NC}"
            microk8s.ctr images import $MICROK8S_BASE_IMAGES_TAR_PATH
            echo "${GREEN}Microk8s offline installation done!${NC}"
        else
            echo "${YELLOW}Installing microk8s v$DEFAULT_MICRO_VERSION ...${NC}"
            snap install microk8s --classic --channel=$DEFAULT_MICRO_VERSION
        fi

        echo "${YELLOW}Stopping microk8s for configuration ...${NC}"
        microk8s.stop

        set +e
        echo "${YELLOW}Enable node_port-range=80-32000 ...${NC}";
        insert_text "--service-node-port-range=80-32000" /var/snap/microk8s/current/args/kube-apiserver
        echo "${YELLOW}Disable insecure port ...${NC}";
        insert_text "--insecure-port=0" /var/snap/microk8s/current/args/kube-apiserver
        insert_text "--runtime-config=admissionregistration.k8s.io/v1beta1=true" /var/snap/microk8s/current/args/kube-apiserver
        
        echo "${YELLOW}Set limit of completed pods to 200 ...${NC}";
        insert_text "--terminated-pod-gc-threshold=200" /var/snap/microk8s/current/args/kube-controller-manager
        set -e

        echo "${YELLOW}Set vm.max_map_count=262144${NC}"
        sysctl -w vm.max_map_count=262144
        set +e
        insert_text "vm.max_map_count=262144" /etc/sysctl.conf
        set -e
        
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

        echo "${YELLOW}Enable microk8s DNS: '$DNS' ...${NC}"
        microk8s.enable dns:$DNS

        echo "${YELLOW}Waiting for DNS to be ready ...${NC}"
        microk8s.kubectl rollout status -n kube-system deployment coredns --timeout=120s

        echo "${YELLOW}Create dir: $USER_HOME/.kube ...${NC}"
        mkdir -p $USER_HOME/.kube

        echo "${YELLOW}Export Kube-Config to $USER_HOME/.kube/config ...${NC}"
        microk8s.kubectl config view --raw | tee $USER_HOME/.kube/config
        chmod 600 $USER_HOME/.kube/config

        echo "${YELLOW}Enable microk8s hostpath-storage ...${NC}"
        microk8s.kubectl enable hostpath-storage

        if [ "$REAL_USER" != "root" ]; then
            echo "${YELLOW} Setting non-root permissions ...${NC}"
            sudo usermod -a -G microk8s $REAL_USER
            sudo chown -f -R $REAL_USER $USER_HOME/.kube
        fi

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
        echo "${GREEN}You can now continue with the platform deployment script.${NC}"
        echo ""
        echo ""
        echo ""
    fi
    echo ""
    echo "${GREEN} DONE ${NC}"
    echo ""
}

function uninstall {
    echo ""
    echo "${YELLOW}Uninstalling Helm ...${NC}"
    snap remove helm --purge && echo "${GREEN}DONE${NC}" || echo "${RED}########################  NOT SUCCESSFUL! ########################${NC}"

    echo "${YELLOW}Uninstalling microk8s ...${NC}"
    snap remove microk8s --purge && echo "${GREEN}DONE${NC}" || echo "${RED}########################  NOT SUCCESSFUL! ########################${NC}"
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

DEFAULT_MICRO_VERSION=1.33/stable
DEFAULT_HELM_VERSION=latest/stable

### Parsing command line arguments:
usage="$(basename "$0")

_Flag: -q   --quiet      will activate quiet mode (default: false)
_Flag:      --uninstall  removes microk8s and helm from the system
_Flag:      --offline    offline installation for snap packages (expects '*.snap' and '*.assert' files within the working dir)

_Argument: -v --version [opt]
where opt is:
    default: $DEFAULT_MICRO_VERSION

_Argument: -os --operating-system [opt]
where opt is:
    AlmaLinux --> AlmaLinux
    Ubuntu    --> Ubuntu
    default: $OS_PRESENT"

QUIET=NA
OFFLINE_SNAPS=NA
DNS=""

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in

        -h|--help)
            echo -e "${YELLOW}$usage ${NC}";
            exit 0
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

        --offline)
            OFFLINE_SNAPS=true
            echo -e "${GREEN}SET OFFLINE_SNAPS: $OFFLINE_SNAPS !${NC}";
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
        install_core core20 # for microk8s
        install_core core24 # for helm
        install_helm
        install_microk8s
    ;;

    "Ubuntu")
        echo -e "${GREEN}Starting Ubuntu installation...${NC}";
        proxy_environment
        install_packages_ubuntu
        install_core core20 # for microk8s
        install_core core24 # for helm
        install_helm
        install_microk8s
    ;;

    *)  
        echo "${RED}Your OS: $OS_PRESENT is not supported at the moment.${NC}"
        echo "${RED}This scripts suppors: Ubuntu and AlmaLinux${NC}"
        echo -e "$usage"
        exit 1
esac