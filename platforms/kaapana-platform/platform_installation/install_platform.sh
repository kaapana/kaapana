#!/bin/bash
set -euf -o pipefail

# if unusual home dir of user: sudo dpkg-reconfigure apparmor

PROJECT_NAME="kaapana-platform"
DEFAULT_VERSION="0.1.0-vdev"

CHART_REGISTRY_URL="https://dktk-jip-registry.dkfz.de/chartrepo"
CHART_REGISTRY_PROJECT="kaapana-public"

CONTAINER_REGISTRY_URL="dktk-jip-registry.dkfz.de"
CONTAINER_REGISTRY_PROJECT="/kaapana"

HTTP_PORT=80
HTTPS_PORT=443
DICOM_PORT=11112
DEV_MODE="true"
DEV_PORTS="false"
GPU_SUPPORT="false"

FAST_DATA_DIR="/home/kaapana"
SLOW_DATA_DIR="/home/kaapana"

PULL_POLICY_PODS="IfNotPresent"
PULL_POLICY_JOBS="IfNotPresent"
PULL_POLICY_OPERATORS="IfNotPresent"

if [ "$DEV_MODE" == "true" ]; then
    PULL_POLICY_PODS="Always"
    PULL_POLICY_JOBS="Always"
    PULL_POLICY_OPERATORS="Always"
fi

CHART_PATH=""
declare -a NEEDED_REPOS=("$CHART_REGISTRY_PROJECT")
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

function import_containerd {
    echo "Starting image import into containerd..."
    docker images --filter=reference="local/*" | tr -s ' ' | cut -d " " -f 1,2 | tr ' ' ':' | tail -n +2 | while read line; do
        echo "Generating tar-file: '$line'"
        docker save $line > ./image.tar
        if [ $? -eq 0 ]; then
            echo "ok"
        else
            echo "Failed!"
            exit 1
        fi
        echo "Import image into containerd..."
        microk8s ctr image import image.tar
        if [ $? -eq 0 ]; then
            echo "ok"
        else
            echo "Failed!"
            exit 1
        fi
        echo "Remove tmp image.tar file..."
        rm image.tar
        if [ $? -eq 0 ]; then
            echo "ok"
        else
            echo "Failed!"
            exit 1
        fi
    done
    echo "All images successfully imported!"
}

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
    echo -e "${YELLOW}Uninstalling releases${NC}"
    helm ls --reverse -A | awk 'NR > 1 { print  "-n "$2, $1}' | xargs -L1 helm delete
    echo -e "${YELLOW}Waiting until everything is terminated...${NC}"
    WAIT_UNINSTALL_COUNT=60
    for idx in $(seq 0 $WAIT_UNINSTALL_COUNT)
    do
        sleep 3
        DEPLOYED_NAMESPACES=$(/bin/bash -i -c "kubectl get namespaces | grep -E --line-buffered 'flow-jobs|flow|base|monitoring|store' | cut -d' ' -f1")
        TERMINATING_PODS=$(/bin/bash -i -c "kubectl get pods --all-namespaces | grep -E --line-buffered 'Terminating' | cut -d' ' -f1")
        UNINSTALL_TEST=$DEPLOYED_NAMESPACES$TERMINATING_PODS
        if [ -z "$UNINSTALL_TEST" ]; then
            break
        fi
    done

    if [ "$idx" -eq "$WAIT_UNINSTALL_COUNT" ]; then
        echo "${RED}Something went wrong while uninstalling please check manually if there are still namespaces or pods floating around. Everything must be delete before the installation:${NC}"
        echo "${RED}kubectl get pods -A${NC}"
        echo "${RED}kubectl get namespaces${NC}"
        echo "${RED}Once everything is delete you can reinstall the platform!${NC}"
        exit 1
    fi

    delete_helm_repos

    echo -e "${GREEN}####################################  UNINSTALLATION DONE  ############################################${NC}"
}

function prefetch_extension_docker {
    echo -e "Prefetching all extension docker container"
    release_name=kube-helm-init-chart-$(echo $(uuidgen --hex) | cut -c1-10)
    helm install --devel --version 0.1-vdev $CHART_REGISTRY_PROJECT/prefetch-extensions-chart \
    --set global.pull_policy_jobs="$PULL_POLICY_JOBS" \
    --set global.registry_url=$CONTAINER_REGISTRY_URL \
    --set global.registry_project=$CONTAINER_REGISTRY_PROJECT \
    --name-template $release_name \
    --wait \
    --atomic \
    --timeout 1m0s
    sleep 10
    helm delete $release_name
    echo -e "${GREEN}OK!${NC}"
}

function download_extensions_and_dags {
    echo -e "Downloading all kaapanadag|kaapanaextensions|kaapanaint to $HOME/.extensions"
    
    set +euf
    updates_output=$(helm repo update)
    set -euf

    if echo "$updates_output" | grep -q 'failed to'; then
        echo -e "${RED}updates failed!${NC}"
        echo -e "${RED}You seem to have no internet connection!${NC}"
        echo "$updates_output"
        exit 1
    else
        mkdir -p $HOME/.extensions
        find $HOME/.extensions/ -type f -delete
        helm pull -d $HOME/.extensions/ --version=1.0-vdev $CHART_REGISTRY_PROJECT/pull-docker-chart
        helm search repo --devel -r '(kaapanadag|kaapanaextension|kaapanaint)' | awk 'NR > 1 { print  $1, "--version " $2}' | xargs -L1 helm pull -d $HOME/.extensions/
        echo -e "${GREEN}Update OK!${NC}"
    fi
}

function install_chart {
    if [ ! -z "$CHART_PATH" ]; then
        CHART_REGISTRY_URL="local"
        CHART_REGISTRY_PROJECT="local"
    else
        add_helm_repos
    fi

    if [ -z "$CHART_REGISTRY_URL" ] || [ -z "$CHART_REGISTRY_PROJECT" ] || [ -z "$CONTAINER_REGISTRY_URL" ]; then
        echo 'CHART_REGISTRY_URL, CHART_REGISTRY_PROJECT, CONTAINER_REGISTRY_URL, CONTAINER_REGISTRY_PROJECT need to be set! -> please adjust the install_platform.sh script!'        
        echo 'ABORT'
        exit 1
    fi
    
    if [ ! "$CONTAINER_REGISTRY_URL" = "local" ];then
        check_credentials
    else
        REGISTRY_USERNAME=""
        REGISTRY_PASSWORD=""
        import_containerd
    fi

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

    download_extensions_and_dags

    if [ ! -z "$CHART_PATH" ]; then
        echo -e "${YELLOW}Installing $PROJECT_NAME: version $chart_version${NC}"
        echo -e "${YELLOW}Chart-tgz-path $CHART_PATH${NC}"
        helm install $CHART_PATH \
        --set global.version="$chart_version" \
        --set global.hostname="$DOMAIN" \
        --set global.dev_ports="$DEV_PORTS" \
        --set global.dev_mode="$DEV_MODE" \
        --set global.dicom_port="$DICOM_PORT" \
        --set global.http_port="$HTTP_PORT" \
        --set global.https_port="$HTTPS_PORT" \
        --set global.fast_data_dir="$FAST_DATA_DIR" \
        --set global.slow_data_dir="$SLOW_DATA_DIR" \
        --set global.home_dir="$HOME" \
        --set global.pull_policy_jobs="$PULL_POLICY_JOBS" \
        --set global.pull_policy_operators="$PULL_POLICY_OPERATORS" \
        --set global.pull_policy_pods="$PULL_POLICY_PODS" \
        --set global.credentials.registry_username="$REGISTRY_USERNAME" \
        --set global.credentials.registry_password="$REGISTRY_PASSWORD" \
        --set global.gpu_support=$GPU_SUPPORT \
        --set global.registry_url=$CONTAINER_REGISTRY_URL \
        --set global.registry_project=$CONTAINER_REGISTRY_PROJECT \
        --name-template $PROJECT_NAME
    else
        echo -e "${YELLOW}Installing $CHART_REGISTRY_PROJECT/$PROJECT_NAME version: $chart_version${NC}"
        helm install --devel --version $chart_version  $CHART_REGISTRY_PROJECT/$PROJECT_NAME \
        --set global.version="$chart_version" \
        --set global.hostname="$DOMAIN" \
        --set global.dev_ports="$DEV_PORTS" \
        --set global.dev_mode="$DEV_MODE" \
        --set global.dicom_port="$DICOM_PORT" \
        --set global.http_port="$HTTP_PORT" \
        --set global.https_port="$HTTPS_PORT" \
        --set global.fast_data_dir="$FAST_DATA_DIR" \
        --set global.slow_data_dir="$SLOW_DATA_DIR" \
        --set global.home_dir="$HOME" \
        --set global.pull_policy_jobs="$PULL_POLICY_JOBS" \
        --set global.pull_policy_operators="$PULL_POLICY_OPERATORS" \
        --set global.pull_policy_pods="$PULL_POLICY_PODS" \
        --set global.credentials.registry_username="$REGISTRY_USERNAME" \
        --set global.credentials.registry_password="$REGISTRY_PASSWORD" \
        --set global.gpu_support=$GPU_SUPPORT \
        --set global.registry_url=$CONTAINER_REGISTRY_URL \
        --set global.registry_project=$CONTAINER_REGISTRY_PROJECT \
        --name-template $PROJECT_NAME
    fi
    
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

    echo "${YELLOW}Upgrading release: $CHART_REGISTRY_PROJECT/$PROJECT_NAME${NC}"
    echo "${YELLOW}version: $chart_version${NC}"

    helm upgrade $PROJECT_NAME $CHART_REGISTRY_PROJECT/$PROJECT_NAME --devel --version $chart_version --set global.version="$chart_version" --reuse-values 
    print_installation_done
}


function check_credentials {
    while true; do
        if [ ! -v REGISTRY_USERNAME ] || [ ! -v REGISTRY_PASSWORD ]; then
            echo -e "${YELLOW}Please enter the credentials for the Container-Registry!${NC}"
            read -p '**** username: ' REGISTRY_USERNAME
            read -s -p '**** password: ' REGISTRY_PASSWORD
        else
            echo -e "${GREEN}Credentials found!${NC}"
            break
        fi
    done
}

function add_helm_repos {
    echo -e "Adding needed helm projects..."
    for i in "${NEEDED_REPOS[@]}"
    do
        echo -e "${YELLOW}Adding project $i.${NC}"
        helm repo add $i $CHART_REGISTRY_URL/$i
    done

    helm repo update
}

function delete_helm_repos {
    # helm repo ls |cut -f 1  | tail -n +2 | xargs -L1 helm repo rm # delete all repos
    echo -e "Deleting needed helm projects..."
    for i in "${NEEDED_REPOS[@]}"
    do
        echo -e "${YELLOW}Deleting project $i.${NC}"
        helm repo remove $i
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

_Argument: --chart-path [path-to-chart-tgz]

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

        --chart-path)
            CHART_PATH="$2"
            echo -e "${GREEN}SET CHART_PATH: $CHART_PATH !${NC}";
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

        --prefetch-extension-docker)
            download_extensions_and_dags
            prefetch_extension_docker
            exit 0
        ;;

        *)    # unknown option
            echo -e "${RED}unknow parameter: $key ${NC}"
            echo -e "${YELLOW}$usage${NC}"
            exit 1
        ;;
    esac
done

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
    options=("Upgrade" "Re-install" "Uninstall" "Quit")
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
            "Uninstall")
                echo -e "${YELLOW}Starting Uninstallation...${NC}"
                delete_deployment
                exit 0
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
