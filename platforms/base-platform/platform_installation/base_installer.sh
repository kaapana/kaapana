#!/bin/bash
#  -*- coding: utf-8; mode: bash; sh-indentation: 4; indent-tabs-mode: nil; sh-basic-offset: 4 -*-
# vi: set fileencoding=utf-8
###########################################
# Version 1.0.2
# @Authors: Jonas Scherer <j.scherer@dkfz.de>, Martin Hettich <m.hettich@dkfz.de>, et al.
# @Copyright: 2019 Deutsches Krebsforschungszentrum http://www.dkfz.de
# @License: Three clauses BSD license
############################################################################80>|###########################################128>|
# set -euf -o pipefail

# set -e
## if a function must not exit on error, use set +e before and set -e after that function. ## TODO!!!


PROJECT_NAME="base-platform"
CHART_REPO="kaapana"
DEFAULT_VERSION="0.9"

FAST_DATA_DIR="/home/kaapana"
SLOW_DATA_DIR="/home/kaapana/dcm_data"

declare -a NEEDED_REPOS=("$CHART_REPO" "camic")




script_name=`basename "$0"`

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


function check_config {
    if [ ! -f "$HOME"/server_config.json ]; then
        echo -e "${RED}Config file not found!${NC}" > /dev/stderr;
        write_config
    else
        echo -e "${GREEN}Config file found!${NC}" > /dev/stderr;
        check_package jq # Should already be installed for network-connection-test -> minimal centos not the case
        if [ ! $QUIET ];then
            while true; do
                read -p "${YELLOW}Do you want to use the existing config? (y/n): ${NC}" yn
                case $yn in
                    [Yy]* ) break;;
                    [Nn]* ) write_config; break;;
                    * ) echo -e "${RED}Please answer y or n.${NC}" > /dev/stderr;
                esac
            done
        fi
    fi
}

function write_config {
    echo -e "Starting write_config..."   > /dev/stderr;
    
    GPU_SUPPORT="false"

    check_package lshw
    
    if lshw -numeric -C display | grep -q 'vendor: NVIDIA' ;then
        echo -e "${GREEN}GPU support enabled!${NC}" > /dev/stderr;
        GPU_SUPPORT="true";
    else
        echo -e "${YELLOW}NO NVIDIA GPU DETECTED !!!!${NC}" > /dev/stderr;
        echo -e "${YELLOW}Install NVIDIA drivers anyway?${NC}" > /dev/stderr;
        while true; do
            read -e -p ">> ONLY IF YOU HAVE A NVIDIA GPU INSTALLED! << (y/n)?" -i "n" yn;
            case $yn in
                [Yy]* ) GPU_SUPPORT="true"; break;;
                [Nn]* ) GPU_SUPPORT="false"; break;;
                * ) echo -e "${RED}Please answer y or n.${NC}" > /dev/stderr;
            esac
        done
    fi
    
    
    echo -e "Check if proxy is set" > /dev/stderr;
    if [ "$http_proxy" = "" ]
    then
        echo -e "${RED}No proxy configuration found!" > /dev/stderr;
        echo -e "Please make sure you used http_proxy and https_proxy (small letters!)${NC}" > /dev/stderr;
        proxy_needed=false
        
    else
        echo -e "${GREEN}Proxy configuration found..." > /dev/stderr;
        echo -e "http_proxy: $http_proxy" > /dev/stderr;
        echo -e "https_proxy: $https_proxy ${NC}" > /dev/stderr;
        proxy_needed=true
    fi
    
    DOMAIN=$(hostname -f)
    IPADDRESS=$(hostname -i | grep -Pom 1 '[0-9.]{7,15}')
    
    if [[ $IPADDRESS =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]] && [[ ! $IPADDRESS == "127.0.0.1" ]]; then
        echo -e "${GREEN}IP-address: $IPADDRESS - ok!${NC}" > /dev/stderr;
        echo -e "${YELLOW}Please check if this is the correct IP address of the server:${NC}" > /dev/stderr;
        read -e -p "**** IP: " -i "$IPADDRESS" IPADDRESS
    else
        echo
        echo -e "${YELLOW}Enter IP-address of the server" > /dev/stderr;
        read -p "**** IP: ${NC}" IPADDRESS
        echo -e "IPADRESS: $IPADDRESS" > /dev/stderr;
    fi

    echo -e ""
    echo -e "${YELLOW}Please enter the domain (FQDN) of the server.${NC}" > /dev/stderr;
    echo -e "${YELLOW}The suggestion could be incorrect!${NC}" > /dev/stderr;
    echo -e "${YELLOW}The IP address should work as well (not recommended - will not work with valid certificates.)${NC}" > /dev/stderr;
    read -e -p "**** server domain (FQDN): " -i "$DOMAIN" DOMAIN

    if [ -z "$DOMAIN" ]; then 
        echo -e "${RED}DOMAIN not set!";  > /dev/stderr;
        echo -e "Please restart the process. ${NC}";  > /dev/stderr;
        exit 1
    else 
        echo -e "${GREEN}Server domain (FQDN): $DOMAIN ${NC}" > /dev/stderr;
    fi

    
cat <<EOF > "$HOME"/server_config.json
{
    "ip_adress_server" : "$IPADDRESS",
    "server_domain" : "$DOMAIN",
    "GPU_SUPPORT" : "$GPU_SUPPORT",
    "proxy_needed" : "$proxy_needed"
}
EOF
    
}


function get_config_value {
    echo -e "Getting config for: $1" > /dev/stderr;
    config_value=$(cat "$HOME"/server_config.json | jq ".$1" | tr -d '"')

    
    if [ $? -ne 0 ] || [ $config_value == null ] || [ -z $config_value ] || [ -z "${config_value+set}" ]; then
        echo -e "${RED}Config value not found...${NC}" > /dev/stderr;
        echo -e "${YELLOW}generating config...${NC}" > /dev/stderr;
        write_config
        get_config_value $1
    fi

    echo -e "Found config - $1: $config_value" > /dev/stderr;
}


function check_package {
    echo -e "Checking if package: $1 "
    rpm -q $1
    if [ $? -eq 0 ];then
        echo -e "${YELLOW}$1 already present! ok ${NC}"  > /dev/stderr;
        
    else
        echo -e "${YELLOW}$1 not found! -> Installing... ${NC}" > /dev/stderr;
        yum install -y $1
        echo -e "${GREEN}$1 installed! ok ${NC}" > /dev/stderr;
    fi
}


function add_helm_path {
    helm_path='/usr/local/bin'
    if [[ $PATH == *"$helm_path"* ]]; then
        echo -e "${YELLOW}Helm path already added!${NC}"
    else
        export PATH=/usr/local/bin:$PATH
        echo -e "${GREEN}Added helm_path to PATH!${NC}"
    fi

}

function print_installation_done {
    echo -e "${GREEN}Installation finished."
    echo -e "Please wait till all components have been downloaded and started."
    echo -e "You can check the progress with:"
    echo -e "watch kubectl get pods --all-namespaces"
    echo -e "When all pod are in the \"running\" or \"completed\" state,"
    echo -e "you can visit: https://$DOMAIN/"
    echo -e "You should be welcomed by the login page."
    echo -e "Default credentials:"
    echo -e "username: admin"
    echo -e "password: KaapanA ${NC}"
}

function install_chart {
    add_helm_path

    if ! [ -x "$(command -v helm)" ]; then
        echo -e "${RED}Install Helm first! ${NC}"
        echo -e "${RED}-> ./$script_name --mode install-helm ${NC}"
        exit 1
    fi

    echo -e "Helm found!"
    helm init --service-account tiller --wait
    

    deployments=$(helm ls|cut -f1)
    echo -e "Current deployments: $deployments"

    if [[ $deployments == *"$PROJECT_NAME"* ]]; then
        echo -e "${YELLOW}$PROJECT_NAME already deployed!${NC}"
        
        read -e -p "Do you want to upgrade (y/n)?: " -i "y";
        if [ $REPLY == "y" ]; then
            upgrade_chart
            exit 0
        else
            read -e -p "Do you want to reinstall (y/n)?: " -i "y";
            if [ $REPLY == "y" ]; then
                echo -e "removing old deployment..."
                helm delete $PROJECT_NAME
                helm delete $PROJECT_NAME --purge
                echo -e "removing namespaces -> (some errors are normal.)"
                kubectl delete namespace --all
                echo -e "Wait 60s ..."
                sleep 60
                echo -e "${GREEN}####################################  DONE  ############################################${NC}"
            else
                echo -e "${GREEN}done.${NC}"
                exit 0
            fi
        fi
    else
        echo -e "No deployment found -> install"
    fi

    check_harbor_access
    helm repo update 

    get_config_value  GPU_SUPPORT
    GPU_SUPPORT=$config_value

    get_config_value  ip_adress_server
    IPADDRESS=$config_value
    get_config_value  server_domain
    DOMAIN=$config_value
    echo -e ""
    read -e -p "Which $PROJECT_NAME version do you want to install?: " -i $DEFAULT_VERSION chart_version;

    helm install --version $chart_version $CHART_REPO/$PROJECT_NAME --set global.hostname="$DOMAIN" --set global.credentials.registry_username="$registry_username" --set global.credentials.registry_password="$registry_password" --set global.gpu_support=$GPU_SUPPORT --set global.fast_data_dir=$FAST_DATA_DIR --set global.slow_data_dir=$SLOW_DATA_DIR --name $PROJECT_NAME
    if [ $? -eq 0 ]; then
        print_installation_done
    else
        echo -e "${RED}An error occurred.${NC}"
        echo -e "${RED}Please check the output and try to rerun with --mode install-helm-chart${NC}"
    fi
    registry_username=""
    registry_password=""
}


function upgrade_chart {
    add_helm_path

    if ! [ -x "$(command -v helm)" ]; then
        echo -e "${RED}Install Helm first! ${NC}"
        echo -e "${RED}-> ./$script_name --mode install-helm ${NC}"
        exit 1
    fi

    echo -e "${GREEN}Helm found! ${NC}"
    helm repo update 

    deployments=$(helm ls|cut -f1)
    echo -e "Current deployments: $deployments"

    echo -e "${YELLOW}$PROJECT_NAME already deployed!${NC}"
    read -e -p "Which version?: " -i $DEFAULT_VERSION chart_version;
    read -e -p "Restart pods (y/n) ?: " -i "n" recreate_pods;
    if [ $recreate_pods == "y" ]; then
        recreate_pods="--recreate-pods"
    else
        recreate_pods=""
    fi

    helm upgrade $PROJECT_NAME $CHART_REPO/$PROJECT_NAME --version $chart_version --reuse-values $recreate_pods
    exit 0

}

function check_harbor_access {
    while true; do
        echo -e "${YELLOW}Please enter the credentials for the DKTK Docker Registry that you got from the kaapana team in order to download docker containers!${NC}"
        read -p '**** username: ' registry_username
        read -s -p '**** password: ' registry_password
        HTTP_RESPONSE=$(curl -u $registry_username:$registry_password --silent --write-out "HTTPSTATUS:%{http_code}"-i -k -X GET "https://dktk-jip-registry.dkfz.de/api/v2.0/projects")

        if [[ $(echo $HTTP_RESPONSE| cut -c1-4 ) == "null" ]];then
            echo -e "${RED}Wrong credentials!${NC}"
            echo -e "${RED}Try again!${NC}"
            continue
        else
            echo ""
            echo -e "${GREEN}Credentials OK!${NC}"
            break
        fi
    done

    echo -e "Checking project access..."
    for i in "${NEEDED_REPOS[@]}"
    do
        if [[ $HTTP_RESPONSE == *"\"name\": \"$i\""* ]];then
            echo -e "${GREEN}Access granted for Project $i.${NC}"
            helm repo add --username $registry_username --password $registry_password $i https://dktk-jip-registry.dkfz.de/chartrepo/$i

        else
            echo -e "${RED}######################### No access for project $i! #########################${NC}"
            echo -e "${RED}################### Please contact the kaapana team from DKFZ to grant access! ###################${NC}"
            exit 1
        fi
    done
}

echo -e "Check if root execution" > /dev/stderr;
if [ "$EUID" -ne 0 ]
then echo -e "${RED}Please run the script with root privileges!${NC}" > /dev/stderr;
    exit
else
    echo -e "${GREEN}OK${NC}" > /dev/stderr;
fi


SIZE=`df -k --output=size "/var/lib" | tail -n1`
if [[ $SIZE -lt 81920 ]]; then
    echo -e "${RED}Your disk space is too small to install the system.${NC}";
    echo -e "${RED}There should be at least 80 GB available @ /var/lib/docker${NC}";
    exit 1;
fi;



QUIET=NA

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"
    
    case $key in
        -m|--mode)
            MODE="$2"
            shift # past argument
            shift # past value
        ;;
        --quiet)
            QUIET=true
            shift # past argument
        ;;
        *)    # unknown option
            POSITIONAL+=("$1") # save it in an array for later
            shift # past argument
        ;;
    esac
done


usage="$(basename "$0") --mode [mode] -- Joint Imaging Platform tools

where mode:
    install-chart - deploys the platform chart on the system
    upgrade-chart - upgrades the platform chart on the system"


echo -e MODE ="${MODE}"


case "$MODE" in
    install-chart)
        install_chart
    ;;

    upgrade-chart)
        upgrade_chart
    ;;
    *)
        echo -e "${RED}$usage${NC}"
        exit 1
esac
if [[ -n $1 ]]; then
    echo -e "${RED}illegal option!${NC}"
    echo -e "${RED}Last line of file specified as non-opt/last argument:${NC}"
    tail -1 "${NREDC}$1${NC}"
fi

#EOF########################################################################80>|###########################################128>|
