#!/bin/bash
set -euf -o pipefail
export HELM_EXPERIMENTAL_OCI=1
# if unusual home dir of user: sudo dpkg-reconfigure apparmor

######################################################
# Main platform configuration
######################################################

PROJECT_NAME="kaapana-platform-chart" # name of the platform Helm chart
PROJECT_ABBR="kp" # abbrevention for the platform-name
DEFAULT_VERSION="0.1.4"    # version of the platform Helm chart

CONTAINER_REGISTRY_URL="" # empty for local build or registry-url like 'dktk-jip-registry.dkfz.de/kaapana' or 'registry.hzdr.de/kaapana/kaapana'
CONTAINER_REGISTRY_USERNAME=""
CONTAINER_REGISTRY_PASSWORD=""

######################################################
# Installation configuration
######################################################

DEV_MODE="true" # dev-mode -> containers will always be re-downloaded after pod-restart
DEV_PORTS="false"
GPU_SUPPORT="false"

HELM_NAMESPACE="kaapana"
PREFETCH_EXTENSIONS="false"
CHART_PATH=""
NO_HOOKS=""

######################################################
# Individual platform configuration
######################################################

CREDENTIALS_MINIO_USERNAME="kaapanaminio"
CREDENTIALS_MINIO_PASSWORD="Kaapana2020"

GRAFANA_USERNAME="admin"
GRAFANA_PASSWORD="admin"

KEYCLOAK_ADMIN_USERNAME="admin"
KEYCLOAK_ADMIN_PASSWORD="Kaapana2020"

FAST_DATA_DIR="/home/kaapana" # Directory on the server, where stateful application-data will be stored (databases, processing tmp data etc.)
SLOW_DATA_DIR="/home/kaapana" # Directory on the server, where the DICOM images will be stored (can be slower)

HTTP_PORT="80"      # -> has to be 80
HTTPS_PORT="443"    # HTTPS port
DICOM_PORT="11112"  # configure DICOM receiver port


INSTANCE_NAME="central"

######################################################

if [ -z ${http_proxy+x} ] || [ -z ${https_proxy+x} ]; then
    http_proxy=""
    https_proxy=""
fi

script_name=`basename "$0"`

# set default values for the colors
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

if ! command -v nvidia-smi &> /dev/null
then
    echo "${YELLOW}No GPU detected...${NC}"
    GPU_SUPPORT="false"
else
    echo "${GREEN}Nvidia GPU detected!${NC}"
    GPU_SUPPORT="true"
fi

function delete_all_images_docker {
    while true; do
        read -e -p "Do you really want to remove all the Docker images from the system?" -i " no" yn
        case $yn in
            [Yy]* ) echo "${GREEN}Removing all images...${NC}" && docker system prune --volumes --all && echo "${GREEN}Done.${NC}"; break;;
            [Nn]* ) echo "${YELLOW}Images will be kept${NC}"; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

function delete_all_images_microk8s {
    while true; do
        read -e -p "Do you really want to remove all the container images from Microk8s?" -i " no" yn
        case $yn in
            [Yy]* ) echo "${GREEN}Removing all images...${NC}" && microk8s.ctr images ls | awk {'print $1'} | xargs microk8s.ctr images rm && echo "${GREEN}Done.${NC}"; break;;
            [Nn]* ) echo "${YELLOW}Images will be kept${NC}"; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
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
    helm -n $HELM_NAMESPACE ls --deployed --failed --pending --superseded --uninstalling --date --reverse | awk 'NR > 1 { print  "-n "$2, $1}' | xargs -L1 -I % sh -c "helm -n $HELM_NAMESPACE uninstall ${NO_HOOKS} --wait --timeout 5m30s %; sleep 2"
    echo -e "${YELLOW}Waiting until everything is terminated...${NC}"
    WAIT_UNINSTALL_COUNT=100
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
    
    echo -e "${YELLOW}Removing namespace kaapana...${NC}"
    microk8s.kubectl delete namespace kaapana --ignore-not-found=true

    if [ "$idx" -eq "$WAIT_UNINSTALL_COUNT" ]; then
        echo "${RED}Something went wrong while uninstalling please check manually if there are still namespaces or pods floating around. Everything must be delete before the installation:${NC}"
        echo "${RED}kubectl get pods -A${NC}"
        echo "${RED}kubectl get namespaces${NC}"
        echo "${RED}Once everything is deleted you can reinstall the platform!${NC}"
        exit 1
    fi


    echo -e "${GREEN}####################################  UNINSTALLATION DONE  ############################################${NC}"
}

function clean_up_kubernetes {
    echo "${YELLOW}Deleting all deployments ${NC}"
    microk8s.kubectl delete deployments --all
    echo "${YELLOW}Deleting all jobs${NC}"
    microk8s.kubectl delete jobs --all
}

function upload_tar {
    echo "${YELLOW}Importing the images fromt the tar, this might take up to one hour...!${NC}"
    microk8s.ctr images import $TAR_PATH
    echo "${GREEN}Finished image uplaod! You should now be able to install the platfrom by specifying the chart path.${NC}"
}

function install_chart {

    if [ -z "$CONTAINER_REGISTRY_URL" ]; then
        echo "${RED}CONTAINER_REGISTRY_URL needs to be set! -> please adjust the install_platform.sh script!${NC}"
        echo "${RED}ABORT${NC}"
        exit 1
    fi


    if [ ! "$QUIET" = "true" ] && [ -z "$CHART_PATH" ];then
        echo -e ""
        read -e -p "${YELLOW}Which $PROJECT_NAME version do you want to install?: ${NC}" -i $DEFAULT_VERSION chart_version;
    else
        chart_version=$DEFAULT_VERSION
    fi

    if [ "$GPU_SUPPORT" = "true" ];then
        echo -e "${GREEN} -> GPU found ...${NC}"
    else
        if [ ! "$QUIET" = "true" ];then
            while true; do
                read -e -p "No Nvidia GPU detected - Enable GPU support anyway?" -i " no" yn
                case $yn in
                    [Yy]* ) echo -e "${GREEN}ENABLING GPU SUPPORT${NC}" && GPU_SUPPORT="true"; break;;
                    [Nn]* ) echo -e "${YELLOW}SET NO GPU SUPPORT${NC}" && GPU_SUPPORT="false"; break;;
                    * ) echo "Please answer yes or no.";;
                esac
            done
        else
            echo -e "${YELLOW}QUIET-MODE active!${NC}"
        fi
    fi

    echo -e "${YELLOW}GPU_SUPPORT: $GPU_SUPPORT ${NC}"
    if [ "$GPU_SUPPORT" = "true" ];then
        echo -e "-> enabling GPU in Microk8s ..."
        if [[ $deployments == *"gpu-operator"* ]];then
            echo -e "-> gpu-operator chart already exists"
        else
            microk8s.enable gpu
        fi
    fi
    get_domain
    
    if [ ! -z "$CHART_PATH" ]; then
        echo -e "${YELLOW}Please note, since you have specified a chart file, you install the platform in OFFLINE_MODE='true'.${NC}"
        echo -e "${YELLOW}We assume that that all images are already presented inside the microk8s.${NC}"
        echo -e "${YELLOW}Images are uploaded either with a previous installation from a docker registry or uploaded from a tar or directly uploaded during building the platform.${NC}"

        if [ $(basename "$CHART_PATH") != "$PROJECT_NAME-$DEFAULT_VERSION.tgz" ]; then
            echo "${RED} Verison of chart_path $CHART_PATH differs from PROJECT_NAME: $PROJECT_NAME and DEFAULT_VERSION: $DEFAULT_VERSION in the installer script.${NC}" 
            exit 1
        fi

        while true; do
        echo -e "${YELLOW}You are installing the platform in offline mode!${NC}"
            read -p "${YELLOW}Please confirm that you are sure that all images are present in microk8s (yes/no): ${NC}" yn
                case $yn in
                    [Yy]* ) break;;
                    [Nn]* ) exit;;
                    * ) echo "Please answer yes or no.";;
                esac
        done

        OFFLINE_MODE="true"
        DEV_MODE="false"
        PULL_POLICY_PODS="IfNotPresent"
        PULL_POLICY_JOBS="IfNotPresent"
        PULL_POLICY_OPERATORS="IfNotPresent"
        PREFETCH_EXTENSIONS="false"

        CONTAINER_REGISTRY_USERNAME=""
        CONTAINER_REGISTRY_PASSWORD=""
    else
        OFFLINE_MODE="false"
        PULL_POLICY_PODS="IfNotPresent"
        PULL_POLICY_JOBS="IfNotPresent"
        PULL_POLICY_OPERATORS="IfNotPresent"

        if [ "$DEV_MODE" == "true" ]; then
            PULL_POLICY_PODS="Always"
            PULL_POLICY_JOBS="Always"
            PULL_POLICY_OPERATORS="Always"
        fi

        echo "${YELLOW}Helm login registry...${NC}"
        check_credentials
        echo "${GREEN}Pulling platform chart from registry...${NC}"
        pull_chart
        SCRIPTPATH=$(dirname "$(realpath $0)")
        CHART_PATH="$SCRIPTPATH/$PROJECT_NAME-$chart_version.tgz"
    fi

    echo "${GREEN}Installing $PROJECT_NAME:$chart_version${NC}"
    echo "${GREEN}CHART_PATH $CHART_PATH${NC}"
    helm -n $HELM_NAMESPACE install --create-namespace $CHART_PATH \
    --set-string global.base_namespace="base" \
    --set-string global.core_namespace="kube-system" \
    --set-string global.credentials_registry_username="$CONTAINER_REGISTRY_USERNAME" \
    --set-string global.credentials_registry_password="$CONTAINER_REGISTRY_PASSWORD" \
    --set-string global.credentials_minio_username="$CREDENTIALS_MINIO_USERNAME" \
    --set-string global.credentials_minio_password="$CREDENTIALS_MINIO_PASSWORD" \
    --set-string global.credentials_grafana_username="$GRAFANA_USERNAME" \
    --set-string global.credentials_grafana_password="$GRAFANA_PASSWORD" \
    --set-string global.credentials_keycloak_admin_username="$KEYCLOAK_ADMIN_USERNAME" \
    --set-string global.credentials_keycloak_admin_password="$KEYCLOAK_ADMIN_PASSWORD" \
    --set-string global.dev_ports="$DEV_PORTS" \
    --set-string global.dicom_port="$DICOM_PORT" \
    --set-string global.fast_data_dir="$FAST_DATA_DIR" \
    --set-string global.flow_namespace="flow" \
    --set-string global.flow_jobs_namespace="flow-jobs" \
    --set-string global.gpu_support="$GPU_SUPPORT" \
    --set-string global.helm_namespace="$HELM_NAMESPACE" \
    --set-string global.home_dir="$HOME" \
    --set-string global.hostname="$DOMAIN" \
    --set-string global.http_port="$HTTP_PORT" \
    --set-string global.http_proxy="$http_proxy" \
    --set-string global.https_port="$HTTPS_PORT" \
    --set-string global.https_proxy="$https_proxy" \
    --set-string global.kaapana_collections[0].name="kaapana-extension-collection" \
    --set-string global.kaapana_collections[0].version="0.1.0" \
    --set-string global.monitoring_namespace="monitoring" \
    --set-string global.meta_namespace="meta" \
    --set-string global.offline_mode="$OFFLINE_MODE" \
    --set-string global.platform_abbr="$PROJECT_ABBR" \
    --set-string global.platform_version="$chart_version" \
    --set-string global.prefetch_extensions="$PREFETCH_EXTENSIONS" \
    --set-string global.preinstall_extensions[0].name="code-server-chart" \
    --set-string global.preinstall_extensions[0].version="4.2.0" \
    --set-string global.preinstall_extensions[1].name="kaapana-plugin-chart" \
    --set-string global.preinstall_extensions[1].version="0.1.1" \
    --set-string global.pull_policy_jobs="$PULL_POLICY_JOBS" \
    --set-string global.pull_policy_operators="$PULL_POLICY_OPERATORS" \
    --set-string global.pull_policy_pods="$PULL_POLICY_PODS" \
    --set-string global.registry_url="$CONTAINER_REGISTRY_URL" \
    --set-string global.release_name="$PROJECT_NAME" \
    --set-string global.slow_data_dir="$SLOW_DATA_DIR" \
    --set-string global.store_namespace="store" \
    --set-string global.version="$chart_version" \
    --set-string global.instance_name="$INSTANCE_NAME" \
    --name-template "$PROJECT_NAME"

    if [ ! -z "$CONTAINER_REGISTRY_USERNAME" ] && [ ! -z "$CONTAINER_REGISTRY_PASSWORD" ]; then
        rm $CHART_PATH
    fi

    print_installation_done
    
    CONTAINER_REGISTRY_USERNAME=""
    CONTAINER_REGISTRY_PASSWORD=""
}


function pull_chart {
    for i in 1 2 3 4 5;
    do
        echo -e "${YELLOW}Pulling chart: ${CONTAINER_REGISTRY_URL}/$PROJECT_NAME with version $chart_version ${NC}"
        helm pull oci://${CONTAINER_REGISTRY_URL}/$PROJECT_NAME --version $chart_version \
            && break \
            || ( echo -e "${RED}Failed -> retry${NC}" && sleep 1 );
        
        if [ $i -eq 5 ];then
            echo -e "${RED}Could not pull chart! -> abort${NC}"
            exit 1
        fi 
    done
}

function check_credentials {
    while true; do
        if [ -z "$CONTAINER_REGISTRY_USERNAME" ] || [ -z "$CONTAINER_REGISTRY_PASSWORD" ]; then
            echo -e "${YELLOW}Please enter the credentials for the Container-Registry!${NC}"
            read -p '**** username: ' CONTAINER_REGISTRY_USERNAME
            read -s -p '**** password: ' CONTAINER_REGISTRY_PASSWORD
        else
            echo -e "${GREEN}Credentials found!${NC}"
            break
        fi
    done
    helm registry login -u $CONTAINER_REGISTRY_USERNAME -p $CONTAINER_REGISTRY_PASSWORD ${CONTAINER_REGISTRY_URL}
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
        auth_proxy_pod=$(microk8s.kubectl get pods -n kube-system |grep oauth2-proxy  | awk '{print $1;}')
        echo "auth_proxy_pod pod: $auth_proxy_pod"
        microk8s.kubectl -n kube-system delete pod $auth_proxy_pod
    fi

    echo -e "${GREEN}DONE${NC}"
}

function print_installation_done {
    echo -e "${GREEN}Installation finished."
    echo -e "Please wait till all components have been downloaded and started."
    echo -e "You can check the progress with:"
    echo -e "watch microk8s.kubectl get pods -A"
    echo -e "When all pod are in the \"running\" or \"completed\" state,${NC}"

    if [ -v DOMAIN ];then
        echo -e "${GREEN}you can visit: https://$DOMAIN:$HTTPS_PORT/"
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

SIZE=`df -k --output=size "/var/snap" | tail -n1`
if [[ $SIZE -lt 81920 ]]; then
    echo -e "${RED}Your disk space is too small to install the system.${NC}";
    echo -e "${RED}There should be at least 80 GiBytes available @ /var/snap ${NC}";
else
    SIZE=`df -h --output=size "/var/snap" | tail -n1`
    echo -e "${GREEN}Check disk space: ok${NC}";
    echo -e "${GREEN}SIZE: $SIZE ${NC}";
fi;


### Parsing command line arguments:
usage="$(basename "$0")

_Flag: --install-certs set new HTTPS-certificates for the platform
_Flag: --remove-all-images-ctr will delete all images from Microk8s (containerd)
_Flag: --remove-all-images-docker will delete all Docker images from the system
_Flag: --quiet, meaning non-interactive operation

_Argument: --version of the platform [version]
_Argument: --username [Docker regsitry username]
_Argument: --password [Docker regsitry password]
_Argument: --port [Set main https-port]
_Argument: --chart-path [path-to-chart-tgz]
_Argument: --upload-tar [path-to-a-tarball]

_Argument: --version [version]

where version is one of the available platform releases:
    0.1.0  --> latest Kaapana release
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
            CONTAINER_REGISTRY_USERNAME="$2"
            echo -e "${GREEN}SET CONTAINER_REGISTRY_USERNAME! $CONTAINER_REGISTRY_USERNAME ${NC}";
            shift # past argument
            shift # past value
        ;;

        -p|--password)
            CONTAINER_REGISTRY_PASSWORD="$2"
            echo -e "${GREEN}SET CONTAINER_REGISTRY_PASSWORD!${NC}";
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

        --upload-tar)
            TAR_PATH="$2"
            echo -e "${GREEN}SET TAR_PATH: $TAR_PATH !${NC}";
            upload_tar
            exit 0
        ;;

        --quiet)
            QUIET=true
            shift # past argument
        ;;

        --install-certs)
            install_certs
            exit 0
        ;;

        --remove-all-images-ctr)
            delete_all_images_microk8s
            exit 0
        ;;

        --remove-all-images-docker)
            delete_all_images_docker
            exit 0
        ;;

        --purge-kube-and-helm)
            echo -e "${YELLOW}Starting Uninstallation...${NC}"
            NO_HOOKS="--no-hooks"
            echo -e "${YELLOW}Using --no-hooks${NC}"
            delete_deployment
            clean_up_kubernetes
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

echo -e "${YELLOW}Get helm deployments...${NC}"
deployments=$(helm -n $HELM_NAMESPACE ls |cut -f1 |tail -n +2)
echo "Current deployments: " 
echo $deployments

if [[ $deployments == *"$PROJECT_NAME"* ]] && [[ ! $QUIET = true ]];then
    echo -e "${YELLOW}$PROJECT_NAME already deployed!${NC}"
    PS3='select option: '
    options=("Re-install" "Uninstall" "Quit")
    select opt in "${options[@]}"
    do
        case $opt in
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