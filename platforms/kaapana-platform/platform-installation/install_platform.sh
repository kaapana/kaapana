#!/bin/bash
set -euf -o pipefail
export HELM_EXPERIMENTAL_OCI=1
# if unusual home dir of user: sudo dpkg-reconfigure apparmor

PROJECT_NAME="kaapana-platform-chart" # name of the platform Helm chart
DEFAULT_VERSION="0.1.1-vdev"    # version of the platform Helm chart

OFFLINE_MODE="false" # true or false
DEV_MODE="true" # dev-mode -> containers will always be re-downloaded after pod-restart

CONTAINER_REGISTRY_URL="" # empty for local build or registry-url like 'dktk-jip-registry.dkfz.de/kaapana' or 'registry.hzdr.de/kaapana/kaapana'

FAST_DATA_DIR="/home/kaapana" # Directory on the server, where stateful application-data will be stored (databases, processing tmp data etc.)
SLOW_DATA_DIR="/home/kaapana" # Directory on the server, where the DICOM images will be stored (can be slower)

HTTP_PORT=80      # not working yet -> has to be 80
HTTPS_PORT=443    # not working yet -> has to be 443
DICOM_PORT=11112  # configure DICOM receiver port

PULL_POLICY_PODS="IfNotPresent"
PULL_POLICY_JOBS="IfNotPresent"
PULL_POLICY_OPERATORS="IfNotPresent"

DEV_PORTS="false"
GPU_SUPPORT="false"

if [ "$DEV_MODE" == "true" ]; then
    PULL_POLICY_PODS="Always"
    PULL_POLICY_JOBS="Always"
    PULL_POLICY_OPERATORS="Always"
fi

if [ "$OFFLINE_MODE" == "true" ]; then
    DEV_MODE="false"
    PULL_POLICY_PODS="Never"
    PULL_POLICY_JOBS="Never"
    PULL_POLICY_OPERATORS="Never"
fi

if [ -z ${http_proxy+x} ] || [ -z ${https_proxy+x} ]; then
    http_proxy=""
    https_proxy=""
fi

CHART_PATH=""
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

function import_containerd {
    echo "${GREEN}Starting image import into containerd...${NC}"
    while true; do
        read -e -p "Should all locally built Docker containers be deleted after the import?" -i " no" yn
        case $yn in
            [Yy]* ) echo -e "${GREEN}Local containers will be removed from Docker after the upload to microk8s${NC}" && DEL_CONTAINERS="true"; break;;
            [Nn]* ) echo -e "${YELLOW}Containers will be kept${NC}" && DEL_CONTAINERS="false"; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
    IMAGE_COUNTER=0
    containerd_imgs=( $(microk8s ctr images ls -q) )
    docker_images_count=$(docker images --filter=reference="local/*" | tr -s ' ' | cut -d " " -f 1,2 | tr ' ' ':' | tail -n +2 | wc -l)
    echo "${GREEN}Found $docker_images_count Docker images to import...${NC}"
    echo 
    docker images --filter=reference="local/*" | tr -s ' ' | cut -d " " -f 1,2 | tr ' ' ':' | tail -n +2 | while read IMAGE; do
        hash=$(docker images --no-trunc --quiet $IMAGE)
        IMAGE_COUNTER=$((IMAGE_COUNTER+1)) 
        echo ""
        echo "${GREEN}Container $IMAGE_COUNTER/$docker_images_count: $IMAGE${NC}"
        if [[ " ${containerd_imgs[*]} " == *"$hash"* ]]; then
            echo "${GREEN}Already found -> ok${NC}"
        else
            echo "${YELLOW}Not found -> generating *.tar ...${NC}"
            docker save $IMAGE > ./image.tar
            if [ $? -eq 0 ]; then
                echo "${GREEN}created.${NC}"
            else
                echo "${RED}Failed to create *.tar of image!${NC}"
                exit 1
            fi
            echo "${GREEN}Import image into containerd...${NC}"
            microk8s ctr image import image.tar
            if [ $? -eq 0 ]; then
                echo "${GREEN}Import ok.${NC}"
            else
                echo "${RED}Failed to import image!${NC}"
                exit 1
            fi
            echo "${GREEN}Remove tmp image.tar file...${NC}"
            rm image.tar
            if [ $? -eq 0 ]; then
                echo "${GREEN}deleted.${NC}"
            else
                echo "${RED}Failed to remove image-tar!${NC}"
                exit 1
            fi
        fi

        if [ "$DEL_CONTAINERS" = "true" ];then
            echo "${GREEN}Deleting Docker-image: $IMAGE${NC}"
            docker rmi $IMAGE
            echo "${GREEN}deleted.${NC}"
        fi
    done

    if [ "$DEL_CONTAINERS" = "true" ];then
        echo "${GREEN}Deleting all remaining Docker-images...${NC}"
        docker system prune --all --force
        echo "${GREEN}done.${NC}"
    fi
    echo "${GREEN}All images successfully imported!${NC}"
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
    helm ls --reverse -A | awk 'NR > 1 { print  "-n "$2, $1}' | xargs -L1 helm uninstall
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

    if [ "$idx" -eq "$WAIT_UNINSTALL_COUNT" ]; then
        echo "${RED}Something went wrong while uninstalling please check manually if there are still namespaces or pods floating around. Everything must be delete before the installation:${NC}"
        echo "${RED}kubectl get pods -A${NC}"
        echo "${RED}kubectl get namespaces${NC}"
        echo "${RED}Once everything is delete you can reinstall the platform!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}####################################  UNINSTALLATION DONE  ############################################${NC}"
}

function prefetch_extensions {
    if [ "$OFFLINE_MODE" == "true" ]; then
        echo "${RED}ERROR: --prefetch-extensions can only be executed when OFFLINE_MODE is set to false. ${NC}"
        echo "${YELLOW}ATTENTION: --prefetch-extensions only works, when you have also installed the platform with OFFLINE_MODE set to false!! ${NC}"
        exit 0
    fi

    echo -e "Prefetching all extension docker container"
    release_name=prefetch-extensions-chart-$(echo $(uuidgen --hex) | cut -c1-10)
    PREFETCH_CHART_PATH=$(find $FAST_DATA_DIR/charts/helpers/ -name "prefetch-extensions*" -type f)
    helm install $PREFETCH_CHART_PATH\
    --set global.pull_policy_pods="$PULL_POLICY_PODS" \
    --set global.registry_url=$CONTAINER_REGISTRY_URL \
    --wait \
    --atomic \
    --timeout 15m0s \
    --name-template $release_name \

    sleep 10
    helm delete $release_name
    echo -e "${GREEN}OK!${NC}"
}

function install_chart {
    if [ ! -z "$CHART_PATH" ]; then
        echo "${GREEN}Setting local chart config.${NC}"
        if [ ! -f $CHART_PATH ]; then
            echo "${RED}Chart file not found at $CHART_PATH!${NC}"
            echo "${RED}Please specify the full absolute path to the chart.tgz-file!${NC}"
            exit 1
        fi
        
        echo "${GREEN}Force PULL_POLICY to 'IfNotPresent' !${NC}"
        DEV_MODE="false"
        PULL_POLICY_PODS="IfNotPresent"
        PULL_POLICY_JOBS="IfNotPresent"
        PULL_POLICY_OPERATORS="IfNotPresent"

        REGISTRY_USERNAME=""
        REGISTRY_PASSWORD=""
        CONTAINER_REGISTRY_URL="local"
        import_containerd

    elif [ -z "$CONTAINER_REGISTRY_URL" ]; then
        echo "${RED}CONTAINER_REGISTRY_URL need to be set! -> please adjust the install_platform.sh script!${NC}"
        echo "${RED}ABORT${NC}"
        exit 1
    elif [ "$OFFLINE_MODE" == "true" ]; then
        REGISTRY_USERNAME=""
        REGISTRY_PASSWORD=""
        echo "${YELLOW}Installing the platform in offline mode${NC}"
    else    
        echo "${YELLOW}Helm login registry...${NC}"
        check_credentials
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
    if [ "$GPU_SUPPORT" = "true" ];then
        echo -e "-> enabling GPU in Microk8s ..."
        microk8s.enable gpu
    fi
    get_domain
    if [ ! "$QUIET" = "true" ];then
        echo -e ""
        read -e -p "${YELLOW}Which $PROJECT_NAME version do you want to install?: ${NC}" -i $DEFAULT_VERSION chart_version;
    else
        chart_version=$DEFAULT_VERSION
    fi

    if [ -z "$CHART_PATH" ]; then
        echo "${GREEN}Pulling platform chart from registry...${NC}"
        pull_chart
        CHART_PATH=$HOME/$PROJECT_NAME
    fi

    echo "${GREEN}Installing $PROJECT_NAME:$chart_version${NC}"
    echo "${GREEN}CHART_PATH $CHART_PATH${NC}"
    helm install $CHART_PATH \
    --set global.version="$chart_version" \
    --set global.hostname="$DOMAIN" \
    --set global.dev_ports="$DEV_PORTS" \
    --set global.offline_mode="$OFFLINE_MODE" \
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
    --set global.http_proxy=$http_proxy \
    --set global.https_proxy=$https_proxy \
    --set global.registry_url=$CONTAINER_REGISTRY_URL \
    --name-template $PROJECT_NAME

    if [ ! -z "$REGISTRY_USERNAME" ] && [ ! -z "$REGISTRY_PASSWORD" ]; then
        rm -rf $CHART_PATH
    fi

    print_installation_done
    
    REGISTRY_USERNAME=""
    REGISTRY_PASSWORD=""
}


function pull_chart {
    if [ "$OFFLINE_MODE" == "false" ]; then
        for i in 1 2 3 4 5;
        do
            echo -e "${YELLOW}Pulling chart: ${CONTAINER_REGISTRY_URL}/$PROJECT_NAME:$chart_version ${NC}"
            helm chart pull ${CONTAINER_REGISTRY_URL}/$PROJECT_NAME:$chart_version \
                && break \
                || ( echo -e "${RED}Failed -> retry${NC}" && sleep 1 );
            
            if [ $i -eq 5 ];then
                echo -e "${RED}Could not pull chart! -> abort${NC}"
                exit 1
            fi 
        done
    fi
    echo -e "${YELLOW}Exporting chart: $HOME/$PROJECT_NAME ${NC}"
    # helm_export=$(helm chart export ${CONTAINER_REGISTRY_URL}/$PROJECT_NAME:$chart_version -d $HOME/)
    # echo $helm_export
    if ! [ -x "$(command helm chart export ${CONTAINER_REGISTRY_URL}/$PROJECT_NAME:$chart_version -d $HOME/)" ]; then
        echo "Successfully exported chart to $HOME/"
    else
        helm chart ls
        echo "${RED}We could not export the chart ${CONTAINER_REGISTRY_URL}/$PROJECT_NAME:$chart_version... please set the OFFLINE_MODE to false ${NC}"
        exit 1
    fi
    
}

function upgrade_chart {
    if [ ! "$QUIET" = "true" ];then
        read -e -p "${YELLOW}Which version should be deployed?: ${NC}" -i $DEFAULT_VERSION chart_version;
    else
        chart_version=$DEFAULT_VERSION
    fi

    echo "${YELLOW}Upgrading release: $PROJECT_NAME ${NC}"
    echo "${YELLOW}version: $chart_version${NC}"
    
    if [ ! -z "$REGISTRY_USERNAME" ] && [ ! -z "$REGISTRY_PASSWORD" ]; then
        CHART_PATH=$HOME/$PROJECT_NAME
        pull_chart
    fi
    echo -e "${YELLOW}Charyt-tgz-path $CHART_PATH${NC}"
    helm upgrade $PROJECT_NAME $CHART_PATH --devel --version $chart_version --set global.version="$chart_version" --reuse-values 
    if [ ! -z "$REGISTRY_USERNAME" ] && [ ! -z "$REGISTRY_PASSWORD" ]; then
        rm -rf $CHART_PATH
    fi
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
    helm registry login -u $REGISTRY_USERNAME -p $REGISTRY_PASSWORD ${CONTAINER_REGISTRY_URL}
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
        louketo_pod=$(microk8s.kubectl get pods -n kube-system |grep louketo  | awk '{print $1;}')
        echo "louketo pod: $louketo_pod"
        microk8s.kubectl -n kube-system delete pod $louketo_pod
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
_Flag: --prefetch-extensions is used to prefetch every docker image which might be needed when installing an extension. You should execute this, if you want to go offline after installation.

_Argument: --chart-path [path-to-chart-tgz]

_Argument: --username [Docker regsitry username]
_Argument: --password [Docker regsitry password]
_Argument: --port [Set main https-port]

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

        --remove-all-images-ctr)
            delete_all_images_microk8s
            exit 0
        ;;

        --remove-all-images-docker)
            delete_all_images_docker
            exit 0
        ;;

        --prefetch-extensions)
            prefetch_extensions
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
