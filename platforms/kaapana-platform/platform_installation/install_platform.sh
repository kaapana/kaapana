#!/bin/bash
############################################################################80>|###########################################128>|
# @Version: 1.0.0
# @Authors: Jonas Scherer <j.scherer@dkfz.de>, Klaus Kades <k.kades@dkfz.de> et al.
# @Copyright: 2019 Deutsches Krebsforschungszentrum http://www.dkfz.de
############################################################################80>|###########################################128>|
set -euf -o pipefail

# if unusual home dir of user: sudo dpkg-reconfigure apparmor

PROJECT_NAME="kaapana-platform"
DEFAULT_VERSION="1.0.0-vdev"
REGISTRY_URL="dktk-jip-registry.dkfz.de"
REGISTRY_PROJECT_CONTAINER="/kaapana"
REGISTRY_PROJECT_CHART="kaapana-public"

HTTP_PORT=80
HTTPS_PORT=443
DICOM_PORT=11112
DEV_MODE="true"
GPU_SUPPORT="false"
DEV_PORTS="false"


FAST_DATA_DIR="/home/kaapana"
SLOW_DATA_DIR="/home/kaapana/dicom"
PULL_POLICY_PODS="Always"
PULL_POLICY_JOBS="Always"
PULL_POLICY_OPERATORS="Always"

declare -a NEEDED_REPOS=("$REGISTRY_PROJECT_CHART" "processing-external")

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

function get_domain {
    DOMAIN=$(hostname -f)

    if [ ! "$QUIET" = "true" ];then
        echo -e ""
        echo -e "${YELLOW}Please enter the domain (FQDN) of the server.${NC}" > /dev/stderr;
        echo -e "${YELLOW}The suggestion could be incorrect!${NC}" > /dev/stderr;
        echo -e "${YELLOW}The IP address should work as well (not recommended - will not work with valid certificates.)${NC}" > /dev/stderr;
        read -e -p "**** server domain (FQDN): " -i "$DOMAIN" DOMAIN
    else
        echo -e "${GREEN}QUIET: true -> DOMAIN: $DOMAIN ${NC}" > /dev/stderr;
    fi

    if [ -z "$DOMAIN" ]; then
        echo -e "${RED}DOMAIN not set!";  > /dev/stderr;
        echo -e "Please restart the process. ${NC}";  > /dev/stderr;
        exit 1
    else
        echo -e "${GREEN}Server domain (FQDN): $DOMAIN ${NC}" > /dev/stderr;
        # Probably no necessary, can be removed in the future!
        # if [[ $DOMAIN =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        #     echo "${YELLOW}Detected an IP address as server domain, adding the IP: $DOMAIN to no_proxy"
        #     INSERTLINE="no_proxy=$no_proxy,$DOMAIN"
        #     grep -q '\bno_proxy\b.*\b'${DOMAIN}'\b' /etc/environment || sed -i '/no_proxy=/d' /etc/environment
        #     grep -q '\bno_proxy\b.*\b'${DOMAIN}'\b' /etc/environment  && echo "$DOMAIN already part of no_proxy ...." ||  sh -c "echo '$INSERTLINE' >> /etc/environment"
        # fi
    fi
}

function delete_deployment {
    echo -e "${YELLOW}Removing deployment: $PROJECT_NAME${NC}"
    helm del $PROJECT_NAME
    echo -e "${YELLOW}Wait 60s until everything is terminated...${NC}"
    sleep 60
    echo -e "${GREEN}####################################  DONE  ############################################${NC}"
}

function install_chart {
    check_harbor_access

    if [ ! "$QUIET" = "true" ];then
        while true; do
            read -e -p "Enable GPU support?" -i " no" yn
            case $yn in
                [Yy]* ) echo -e "${GREEN}ENABLING GPU SUPPORT${NC}" && GPU_SUPPORT="true"; break;;
                [Nn]* ) echo -e "${YELLOW}SET NO GPU SUPPORT${NC}" && GPU_SUPPORT="false"; break;;
                * ) echo "Please answer yes or no.";;
            esac
        done
    else
        echo -e "${YELLOW}QUIET-MODE active!${NC}"
    fi
    
    echo -e "${YELLOW}GPU_SUPPORT: $GPU_SUPPORT ${NC}"

    get_domain
    if [ ! "$QUIET" = "true" ];then
        echo -e ""
        read -e -p "${YELLOW}Which $PROJECT_NAME version do you want to install?: ${NC}" -i $DEFAULT_VERSION chart_version;
    else
        chart_version=$DEFAULT_VERSION
    fi
    
    echo -e "${YELLOW}Installing $REGISTRY_PROJECT_CHART/$PROJECT_NAME version: $chart_version${NC}"
    helm install --devel --version $chart_version  $REGISTRY_PROJECT_CHART/$PROJECT_NAME \
    --set global.version="$chart_version" \
    --set global.hostname="$DOMAIN" \
    --set global.dev_ports="$DEV_PORTS" \
    --set global.dev_mode="$DEV_MODE" \
    --set global.dicom_port="$DICOM_PORT" \
    --set global.http_port="$HTTP_PORT" \
    --set global.https_port="$HTTPS_PORT" \
    --set global.fast_data_dir="$FAST_DATA_DIR" \
    --set global.slow_data_dir="$SLOW_DATA_DIR" \
    --set global.pull_policy_jobs="$PULL_POLICY_JOBS" \
    --set global.pull_policy_operators="$PULL_POLICY_OPERATORS" \
    --set global.pull_policy_pods="$PULL_POLICY_PODS" \
    --set global.credentials.registry_username="$REGISTRY_USERNAME" \
    --set global.credentials.registry_password="$REGISTRY_PASSWORD" \
    --set global.gpu_support=$GPU_SUPPORT \
    --set global.registry_url=$REGISTRY_URL \
    --set global.registry_project=$REGISTRY_PROJECT_CONTAINER \
    --name-template $PROJECT_NAME
    
    print_installation_done
    
    REGISTRY_USERNAME=""
    REGISTRY_PASSWORD=""
}


function upgrade_chart {
    if [ ! "$QUIET" = "true" ];then
        read -e -p "${YELLOW}Which version should be deployed?: ${NC}" -i $DEFAULT_VERSION chart_version;
    else
        chart_version=$DEFAULT_VERSION
    fi

    echo "${YELLOW}Upgrading release: $REGISTRY_PROJECT_CHART/$PROJECT_NAME${NC}"
    echo "${YELLOW}version: $chart_version${NC}"

    helm upgrade $PROJECT_NAME $REGISTRY_PROJECT_CHART/$PROJECT_NAME --devel --version $chart_version --set global.version="$chart_version" --reuse-values 
    print_installation_done
}


function check_harbor_access {
    echo -e "${YELLOW}Check registry access...${NC}"
    while true; do
        if [ ! -v REGISTRY_USERNAME ] || [ ! -v REGISTRY_PASSWORD ]; then
            echo -e "${YELLOW}Please enter the credentials for the DKTK Docker Registry that you got from the kaapana team in order to download docker containers!${NC}"
            read -p '**** username: ' REGISTRY_USERNAME
            read -s -p '**** password: ' REGISTRY_PASSWORD
        else
            echo -e "${GREEN}Credentials already found!${NC}"
        fi

        HTTP_STATUS=$(curl -u $REGISTRY_USERNAME:$REGISTRY_PASSWORD --silent --write-out "%{http_code}" --output /dev/null "https://dktk-jip-registry.dkfz.de/api/v2.0/users/current")
        if [[ "$HTTP_STATUS" -ne 200 ]];then
            echo -e "${RED}Wrong credentials!${NC}"
            echo -e "${RED}Try again!${NC}"
            unset REGISTRY_USERNAME
            unset REGISTRY_PASSWORD
            continue
        else
            echo ""
            echo -e "${GREEN}Credentials OK!${NC}"
            break
        fi
    done

    echo -e "Checking project access..."
    HTTP_RESPONSE=$(curl -u $REGISTRY_USERNAME:$REGISTRY_PASSWORD --silent --write-out "HTTPSTATUS:%{http_code}"-i -k -X GET "https://dktk-jip-registry.dkfz.de/api/v2.0/projects")
    for i in "${NEEDED_REPOS[@]}"
    do
        if [[ $HTTP_RESPONSE == *"\"name\": \"$i\""* ]];then
            echo -e "${GREEN}Access granted for Project $i.${NC}"
            helm repo add --username $REGISTRY_USERNAME --password $REGISTRY_PASSWORD $i https://dktk-jip-registry.dkfz.de/chartrepo/$i

        else
            echo -e "${RED}######################### No access for project $i! #########################${NC}"
            echo -e "${RED}################### Please contact the kaapana team from DKFZ to grant access! ###################${NC}"
            exit 1
        fi
    done
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

function print_installation_done {
    echo -e "${GREEN}Installation finished."
    echo -e "Please wait till all components have been downloaded and started."
    echo -e "You can check the progress with:"
    echo -e "watch microk8s.kubectl get pods --all-namespaces"
    echo -e "When all pod are in the \"running\" or \"completed\" state,${NC}"

    if [ -v DOMAIN ];then
        echo -e "${GREEN}you can visit: https://$DOMAIN/"
        echo -e "You should be welcomed by the login page."
        echo -e "Initial credentials:"
        echo -e "username: kaapana"
        echo -e "password: kaapana ${NC}"
    fi
}

### MAIN programme body:

if [ "$EUID" -eq 0 ];then
    echo -e "${RED}Please run the script without root privileges!${NC}";
    # exit 1
else
    echo -e "${YELLOW}USER: $USER ${NC}";
fi

SIZE=`df -k --output=size "/var/lib" | tail -n1`
if [[ $SIZE -lt 81920 ]]; then
    echo -e "${RED}Your disk space is too small to install the system.${NC}";
    echo -e "${RED}There should be at least 80 GiBytes available @ /var/lib/docker${NC}";
    exit 1;
else
    SIZE=`df -h --output=size "/var/lib" | tail -n1`
    echo -e "${GREEN}Check disk space: ok${NC}";
    echo -e "${GREEN}SIZE: $SIZE ${NC}";
fi;


### Parsing command line arguments:
usage="$(basename "$0")

_Flag: --install-certs  set new HTTPS-certificates for the platform
_Flag: --quiet, meaning non-interactive operation

_Argument: --username [Docker regsitry username]
_Argument: --password [Docker regsitry password]
_Argument: --port [Set main https-port]


_Argument: --version [version]

where version is one of the available platform releases:
    1.1          --> latest JIP release
    $DEFAULT_VERSION  --> latest development version ${NC}"

QUIET=NA

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        -v|--version)
            DEFAULT_VERSION="$2"
            shift # past argument
            shift # past value
        ;;

        -u|--username)
            REGISTRY_USERNAME="$2"
            echo -e "${GREEN}SET REGISTRY_USERNAME! $REGISTRY_USERNAME ${NC}";
            shift # past argument
            shift # past value
        ;;

        -p|--password)
            REGISTRY_PASSWORD="$2"
            echo -e "${GREEN}SET REGISTRY_PASSWORD!${NC}";
            shift # past argument
            shift # past value
        ;;

        --port)
            HTTPS_PORT="$2"
            echo -e "${GREEN}SET PORT!${NC}";
            shift # past argument
            shift # past value
        ;;

        --quiet)
            QUIET=true
            shift # past argument
        ;;

        --install-certs)
            install_certs
            exit 0
        ;;

        *)    # unknown option
            echo -e "${RED}unknow parameter: $key ${NC}"
            echo -e "${YELLOW}$usage${NC}"
            exit 1
        ;;
    esac
done

echo -e "${YELLOW}Check if curl is available...${NC}"
if ! [ -x "$(command -v curl)" ]; then
    echo -e "${RED}############### Curl not available! ###############${NC}"
    echo -e "${YELLOW}       Install curl first! ${NC}"
    exit 1
else
    echo -e "${GREEN}ok${NC}"
fi

echo -e "${YELLOW}Check if helm is available...${NC}"
if ! [ -x "$(command -v helm)" ]; then
    echo -e "${RED}############### Helm not available! ###############${NC}"
    echo -e "${YELLOW}       Install server dependencies first! ${NC}"
    exit 1
else
    echo -e "${GREEN}ok${NC}"
fi

echo -e "${YELLOW}Update helm repos...${NC}"

set +euf
updates_output=$(helm repo update)
set -euf

if echo "$updates_output" | grep -q 'failed to'; then
    echo -e "${RED}updates failed!${NC}"
    echo "$updates_output"
    exit 1
else
    echo -e "${GREEN}updates ok${NC}" 
fi

echo -e "${YELLOW}Get helm deployments...${NC}"
deployments=$(helm ls |cut -f1 |tail -n +2)
echo "Current deployments: " 
echo $deployments

if [[ $deployments == *"$PROJECT_NAME"* ]] && [[ ! $QUIET = true ]];then
    echo -e "${YELLOW}$PROJECT_NAME already deployed!${NC}"
    PS3='select option: '
    options=("Upgrade" "Re-install" "Quit")
    select opt in "${options[@]}"
    do
        case $opt in
            "Upgrade")
                echo -e "${YELLOW}Starting upgrade...${NC}"
                upgrade_chart
                break
                ;;
            "Re-install")
                echo -e "${YELLOW}Starting re-installation...${NC}"
                delete_deployment
                install_chart
                break
                ;;
            "Quit")
                echo -e "${YELLOW}abort.${NC}"
                exit 0
                ;;
            *) echo "invalid option $REPLY";;
        esac
    done
elif [[ $deployments == *"$PROJECT_NAME"* ]] && [[ $QUIET = true ]];then
    echo -e "${RED}Project already deplyed!${NC}"
    echo -e "${RED}abort.${NC}"
    exit 1

else
    echo -e "${GREEN}No previous deployment found -> installation${NC}"
    install_chart
fi
