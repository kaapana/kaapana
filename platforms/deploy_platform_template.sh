#!/bin/bash
set -euf -o pipefail
export HELM_EXPERIMENTAL_OCI=1
# if unusual home dir of user: sudo dpkg-reconfigure apparmor

######################################################
# Main platform configuration
######################################################

PLATFORM_NAME="{{ platform_name }}" # name of the platform Helm chart
PLATFORM_BUILD_VERSION="{{ platform_build_version }}"    # version of the platform Helm chart -> auto-generated
PLATFORM_BUILD_BRANCH="{{ platform_build_branch }}"    # branch name, which was build from -> auto-generated
PLATFORM_LAST_COMMIT_TIMESTAMP="{{ platform_last_commit_timestamp }}" # timestamp of the last commit -> auto-generated
PLATFORM_BUILD_TIMESTAMP="{{ platform_build_timestamp }}"    # timestamp of the build-time -> auto-generated

CONTAINER_REGISTRY_URL="{{ container_registry_url|default('', true) }}" # empty for local build or registry-url like 'dktk-jip-registry.dkfz.de/kaapana' or 'registry.hzdr.de/kaapana/kaapana'
CONTAINER_REGISTRY_USERNAME="{{ container_registry_username|default('', true) }}"
CONTAINER_REGISTRY_PASSWORD="{{ container_registry_password|default('', true) }}"

######################################################
# Deployment configuration
######################################################

DEV_MODE="{{ dev_mode|default('true', true) }}" # dev-mode -> containers will always be re-downloaded after pod-restart
DEV_PORTS="{{ dev_ports|default('false') }}"
GPU_SUPPORT="{{ gpu_support|default('false') }}"

PREFETCH_EXTENSIONS="{{ prefetch_extensions|default('false') }}"
CHART_PATH=""
NO_HOOKS=""
ENABLE_NFS=false

INSTANCE_UID=""
SERVICES_NAMESPACE="{{ services_namespace }}"
ADMIN_NAMESPACE="{{ admin_namespace }}"
JOBS_NAMESPACE="{{ jobs_namespace }}"
EXTENSIONS_NAMESPACE="{{ extensions_namespace }}"
HELM_NAMESPACE="{{ helm_namespace }}"

INCLUDE_REVERSE_PROXY=false
######################################################
# Individual platform configuration
######################################################

CREDENTIALS_MINIO_USERNAME="{{ credentials_minio_username|default('kaapanaminio', true) }}"
CREDENTIALS_MINIO_PASSWORD="{{ credentials_minio_password|default('Kaapana2020', true) }}"

GRAFANA_USERNAME="{{ credentials_grafana_username|default('admin', true) }}"
GRAFANA_PASSWORD="{{ credentials_grafana_password|default('admin', true) }}"

KEYCLOAK_ADMIN_USERNAME="{{ credentials_keycloak_admin_username|default('admin', true) }}"
KEYCLOAK_ADMIN_PASSWORD="{{ credentials_keycloak_admin_password|default('Kaapana2020', true) }}"

FAST_DATA_DIR="{{ fast_data_dir|default('/home/kaapana')}}" # Directory on the server, where stateful application-data will be stored (databases, processing tmp data etc.)
SLOW_DATA_DIR="{{ slow_data_dir|default('/home/kaapana')}}" # Directory on the server, where the DICOM images will be stored (can be slower)

HTTP_PORT="{{ http_port|default(80)|int }}"      # -> has to be 80
HTTPS_PORT="{{ https_port|default(443) }}"    # HTTPS port
DICOM_PORT="{{ dicom_port|default(11112) }}"  # configure DICOM receiver port

{% for item in additional_env %}
{{ item.name }}="{{ item.default_value }}"{% if item.comment %} # {{item.comment}}{% endif %}
{%- endfor %}

######################################################

if [ -z ${http_proxy+x} ] || [ -z ${https_proxy+x} ]; then
    http_proxy=""
    https_proxy=""
fi


if [ ! -z $INSTANCE_UID ]; then
    echo ""
    echo "Setting INSTANCE_UID: $INSTANCE_UID namespaces ..."
    SERVICES_NAMESPACE="$INSTANCE_UID-$SERVICES_NAMESPACE"
    # ADMIN_NAMESPACE="$INSTANCE_UID-$ADMIN_NAMESPACE"
    JOBS_NAMESPACE="$INSTANCE_UID-$JOBS_NAMESPACE"
    EXTENSIONS_NAMESPACE="$INSTANCE_UID-$EXTENSIONS_NAMESPACE"
    HELM_NAMESPACE="$INSTANCE_UID-$HELM_NAMESPACE"

    FAST_DATA_DIR="$FAST_DATA_DIR-$INSTANCE_UID"
    SLOW_DATA_DIR="$SLOW_DATA_DIR-$INSTANCE_UID"
    
    INCLUDE_REVERSE_PROXY=true
fi
echo ""
echo "JOBS_NAMESPACE:       $JOBS_NAMESPACE "
echo "HELM_NAMESPACE:       $HELM_NAMESPACE "
echo "ADMIN_NAMESPACE:      $ADMIN_NAMESPACE "
echo "SERVICES_NAMESPACE:   $SERVICES_NAMESPACE "
echo "EXTENSIONS_NAMESPACE: $EXTENSIONS_NAMESPACE "
echo ""
echo "FAST_DATA_DIR: $FAST_DATA_DIR "
echo "SLOW_DATA_DIR: $SLOW_DATA_DIR "
echo ""

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

if command -v nvidia-smi &> /dev/null && nvidia-smi
then
    echo "${GREEN}Nvidia GPU detected!${NC}"
    GPU_SUPPORT="true"
else
    echo "${YELLOW}No GPU detected...${NC}"
    GPU_SUPPORT="false"
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

    if [ -z ${DOMAIN+x} ]; then
        echo -e ""
        DOMAIN=$(hostname -f)
    else
        echo -e "${GREEN}Server domain (FQDN): $DOMAIN ${NC}" > /dev/stderr;
    fi

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
    echo -e "${YELLOW}Undeploy releases${NC}"
    helm -n $HELM_NAMESPACE ls --deployed --failed --pending --superseded --uninstalling --date --reverse | awk 'NR > 1 { print  "-n "$2, $1}' | xargs -L1 -I % sh -c "helm -n $HELM_NAMESPACE uninstall ${NO_HOOKS} --wait --timeout 5m30s %; sleep 2"
    echo -e "${YELLOW}Waiting until everything is terminated ...${NC}"
    WAIT_UNINSTALL_COUNT=100
    for idx in $(seq 0 $WAIT_UNINSTALL_COUNT)
    do
        sleep 3
        DEPLOYED_NAMESPACES=$(/bin/bash -i -c "kubectl get namespaces | grep -E --line-buffered '$JOBS_NAMESPACE|$EXTENSIONS_NAMESPACE' | cut -d' ' -f1")
        TERMINATING_PODS=$(/bin/bash -i -c "kubectl get pods --all-namespaces | grep -E --line-buffered 'Terminating' | cut -d' ' -f1")
        echo -e ""
        UNINSTALL_TEST=$DEPLOYED_NAMESPACES$TERMINATING_PODS
        if [ -z "$UNINSTALL_TEST" ]; then
            break
        else
            echo -e "${YELLOW}Waiting for $TERMINATING_PODS $DEPLOYED_NAMESPACES ${NC}"
        fi
    done
    
    echo -e "${YELLOW}Removing namespace $HELM_NAMESPACE ...${NC}"
    microk8s.kubectl delete namespace $HELM_NAMESPACE --ignore-not-found=true

    if [ "$idx" -eq "$WAIT_UNINSTALL_COUNT" ]; then
        echo "${RED}Something went wrong while undeployment please check manually if there are still namespaces or pods floating around. Everything must be delete before the deployment:${NC}"
        echo "${RED}kubectl get pods -A${NC}"
        echo "${RED}kubectl get namespaces${NC}"
        echo "${RED}Executing './deploy_platform.sh --no-hooks' is an option to force the resources to be removed.${NC}"        
        echo "${RED}Once everything is deleted you can re-deploy the platform!${NC}"
        exit 1
    fi


    echo -e "${GREEN}####################################  UNDEPLOYMENT DONE  ############################################${NC}"
}

function nuke_pods {
    for namespace in $JOBS_NAMESPACE $EXTENSIONS_NAMESPACE $SERVICES_NAMESPACE $ADMIN_NAMESPACE $HELM_NAMESPACE; do
        echo "${RED}Deleting all pods from namespaces: $namespace ...${NC}"; 
        for mypod in $(microk8s.kubectl get pods -n $namespace -o jsonpath="{.items[*].metadata.name}");
        do
            echo "${RED}Deleting: $mypod ${NC}"; 
            microk8s.kubectl delete pod -n $namespace $mypod --grace-period=0 --force 
        done
    done
}


function clean_up_kubernetes {
    for n in $EXTENSIONS_NAMESPACE $JOBS_NAMESPACE $HELM_NAMESPACE;
    do
        echo "${YELLOW}Deleting namespace ${n} with all its resources ${NC}"
        microk8s.kubectl delete --ignore-not-found namespace $n
    done
    echo "${YELLOW}Deleting all deployments in namespace default ${NC}"
    microk8s.kubectl delete deployments --all
    echo "${YELLOW}Deleting all jobs in namespace default ${NC}"
    microk8s.kubectl delete jobs --all
    echo "${YELLOW}Removing remove-secret job${NC}"
    microk8s.kubectl -n $SERVICES_NAMESPACE delete job --ignore-not-found remove-secret
}

function upload_tar {
    echo "${YELLOW}Importing the images from the tar, this might take up to one hour...!${NC}"
    microk8s.ctr images import $TAR_PATH
    echo "${GREEN}Finished image upload! You should now be able to deploy the platform by specifying the chart path.${NC}"
}

function deploy_chart {

    if [ -z "$CONTAINER_REGISTRY_URL" ]; then
        echo "${RED}CONTAINER_REGISTRY_URL needs to be set! -> please adjust the deploy_platform.sh script!${NC}"
        echo "${RED}ABORT${NC}"
        exit 1
    fi

    chart_version=$PLATFORM_BUILD_VERSION

    get_domain
    
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
    
    if [ ! -z "$CHART_PATH" ]; then
        echo -e "${YELLOW}Please note, since you have specified a chart file, you deploy the platform in OFFLINE_MODE='true'.${NC}"
        echo -e "${YELLOW}We assume that that all images are already presented inside the microk8s.${NC}"
        echo -e "${YELLOW}Images are uploaded either with a previous deployment from a docker registry or uploaded from a tar or directly uploaded during building the platform.${NC}"

        if [ $(basename "$CHART_PATH") != "$PLATFORM_NAME-$PLATFORM_BUILD_VERSION.tgz" ]; then
            echo "${RED} Version of chart_path $CHART_PATH differs from PROJECT_NAME: $PLATFORM_NAME and PLATFORM_BUILD_VERSION: $PLATFORM_BUILD_VERSION in the deployment script.${NC}" 
            exit 1
        fi

        while true; do
        echo -e "${YELLOW}You are deploying the platform in offline mode!${NC}"
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
        SCRIPT_PATH=$(dirname "$(realpath $0)")
        pull_chart $SCRIPT_PATH
        CHART_PATH="$SCRIPT_PATH/$PLATFORM_NAME-$chart_version.tgz"
    fi

    echo "${GREEN}Deploying $PLATFORM_NAME:$chart_version${NC}"
    echo "${GREEN}CHART_PATH $CHART_PATH${NC}"
    helm -n $HELM_NAMESPACE install --create-namespace $CHART_PATH \
    --set-string global.base_namespace="base" \
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
    --set-string global.services_namespace=$SERVICES_NAMESPACE \
    --set-string global.jobs_namespace=$JOBS_NAMESPACE \
    --set-string global.extensions_namespace=$EXTENSIONS_NAMESPACE \
    --set-string global.admin_namespace=$ADMIN_NAMESPACE \
    --set-string global.gpu_support="$GPU_SUPPORT" \
    --set-string global.helm_namespace="$HELM_NAMESPACE" \
    --set global.enable_nfs=$ENABLE_NFS \
    --set global.include_reverse_proxy=$INCLUDE_REVERSE_PROXY \
    --set-string global.home_dir="$HOME" \
    --set-string global.hostname="$DOMAIN" \
    --set-string global.http_port="$HTTP_PORT" \
    --set-string global.http_proxy="$http_proxy" \
    --set-string global.https_port="$HTTPS_PORT" \
    --set-string global.https_proxy="$https_proxy" \
    {% for item in kaapana_collections -%}
    --set-string global.kaapana_collections[{{loop.index0}}].name="{{ item.name }}" \
    --set-string global.kaapana_collections[{{loop.index0}}].version="{{ item.version }}" \
    {% endfor -%}
    --set-string global.offline_mode="$OFFLINE_MODE" \
    --set-string global.prefetch_extensions="$PREFETCH_EXTENSIONS" \
    {% for item in preinstall_extensions -%}
    --set-string global.preinstall_extensions[{{loop.index0}}].name="{{ item.name }}" \
    --set-string global.preinstall_extensions[{{loop.index0}}].version="{{ item.version }}" \
    {% endfor -%}
    --set-string global.pull_policy_jobs="$PULL_POLICY_JOBS" \
    --set-string global.pull_policy_operators="$PULL_POLICY_OPERATORS" \
    --set-string global.pull_policy_pods="$PULL_POLICY_PODS" \
    --set-string global.registry_url="$CONTAINER_REGISTRY_URL" \
    --set-string global.release_name="$PLATFORM_NAME" \
    --set-string global.build_timestamp="$PLATFORM_BUILD_TIMESTAMP" \
    --set-string global.kaapana_build_version="$PLATFORM_BUILD_VERSION" \
    --set-string global.platform_build_branch="$PLATFORM_BUILD_BRANCH" \
    --set-string global.platform_last_commit_timestamp="$PLATFORM_LAST_COMMIT_TIMESTAMP" \
    --set-string global.slow_data_dir="$SLOW_DATA_DIR" \
    --set-string global.instance_uid="$INSTANCE_UID" \
    {% for item in additional_env -%}--set-string {{ item.helm_path }}="${{ item.name }}" \
    {% endfor -%}
    --name-template "$PLATFORM_NAME"

    if [ ! -z "$CONTAINER_REGISTRY_USERNAME" ] && [ ! -z "$CONTAINER_REGISTRY_PASSWORD" ]; then
        rm $CHART_PATH
    fi

    print_deployment_done
    
    CONTAINER_REGISTRY_USERNAME=""
    CONTAINER_REGISTRY_PASSWORD=""
}


function pull_chart {
    for i in 1 2 3 4 5;
    do
        echo -e "${YELLOW}Pulling chart: ${CONTAINER_REGISTRY_URL}/$PLATFORM_NAME with version $chart_version ${NC}"
        helm pull oci://${CONTAINER_REGISTRY_URL}/$PLATFORM_NAME --version $chart_version -d $1 \
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
    if [ ! -f ./tls.key ] || [ ! -f ./tls.crt ]; then
        echo -e "${RED}tls.key or tls.crt could not been found in this directory.${NC}"
        echo -e "${RED}Please rename and copy the files first!${NC}"
        exit 1
    else
        echo -e "files found!"
        echo -e "Creating cluster secret ..."
        microk8s.kubectl delete secret certificate -n $SERVICES_NAMESPACE
        microk8s.kubectl create secret tls certificate --namespace $SERVICES_NAMESPACE --key ./tls.key --cert ./tls.crt
        auth_proxy_pod=$(microk8s.kubectl get pods -n $SERVICES_NAMESPACE |grep oauth2-proxy  | awk '{print $1;}')
        echo "auth_proxy_pod pod: $auth_proxy_pod"
        microk8s.kubectl -n $SERVICES_NAMESPACE delete pod $auth_proxy_pod
    fi

    echo -e "${GREEN}DONE${NC}"
}

function print_deployment_done {
    echo -e "${GREEN}Deployment done."
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



function preflight_checks {
    echo -e "${GREEN}#################################  RUNNING PREFLIGHT CHECKS  #########################################${NC}"

    # Holds the state of the setup after preflight checks:
    # 0 = OK
    # 100=POTENTIAL PROBLEMS - could lead to upstream problems
    # 200=MANIFESTED PROBLEMS - very probably lead to problems
    # 300=CATASTROPHIC PROBLEMS - definitely leads to problems, continuation not possible

    # Since bash has no support for multidimensional arrays every test needs to add exactly one element to this arrays
    SEVERITY=()
    TEST_FAILDS=()
    TEST_NAMES=()
    RESULT_MSGS=()

    # ------ Tests
    SEVERITY+=(200)
    TEST_NAMES+=("Check if user is non-root")
    if [ "$EUID" -eq 0 ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Please run the script without root privileges!")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("(user: $USER)")
    fi

    SEVERITY+=(200)
    TEST_NAMES+=("Check if enough disk-space")
    SIZE="$(df -k --output=size /var/snap | tail -n1)"
    if [ "$SIZE" -lt 81920000 ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Your disk space is too small to deploy the system.\nThere should be at least 80 GiBytes available @ /var/snap")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("(size: $SIZE)")
    fi

    SEVERITY+=(300)
    TEST_NAMES+=("Check that helm is available")
    if ! [ -x "$(command -v helm)" ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Install server dependencies first!")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    fi

    SEVERITY+=(300)
    TEST_NAMES+=("Check that kubectl is installed")
    if ! [ -x $(command -v microk8s.kubectl >/dev/null 2>&1) ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Install server dependencies first!")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    fi

    SEVERITY+=(100)
    TEST_NAMES+=("Check that \$KUBECONFIG is untouched")
    if [ -v KUBECONFIG ]; then
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("In your environment the \$KUBECONFIG variable is set, this is unconventional and can cause to problems (KUBECONFIG=$KUBECONFIG)")
    else
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    fi

    SEVERITY+=(100)
    TEST_NAMES+=("Check if ~/.kube/config matches microk8s config")
    if [ "$(cat /home/$USER/.kube/config)" == "$(microk8s.kubectl config view --raw)" ]; then
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    else
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Your kubeconfig differs from the microk8s version.")
    fi

    SEVERITY+=(100)
    GROUPNAME="microk8s"
    TEST_NAMES+=("Check if user is member of $GROUPNAME...")
    if id -nG "$USER" | grep -qw "$GROUPNAME"; then
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    else
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("")
    fi

    SEVERITY+=(300)
    TEST_NAMES+=("Check if kubectl is working")
    microk8s.kubectl get pods --all-namespaces &> /dev/null
    if [ $? -eq 0 ]; then
        TEST_FAILDS+=(false)
        RESULT_MSGS+=("")
    else
        TEST_FAILDS+=(true)
        RESULT_MSGS+=("Kubectl could not communicate with the server.\nHave a look at the output,\nCheck if the correct server certificate file is in place @ ~/.kube/config,\nCheck if the IP address in the certificate matches the IP address of the server\nand try again.")
    fi


    # Reporting Table
    printf "%-4s %-60s %-15s\n" "Sev" "Test" "Result"
    for i in ${!SEVERITY[@]}; do

        if [ "${TEST_FAILDS[$i]}" = true ]; then
            if [ "${SEVERITY[$i]}" -ge 200 ]; then
                STATUS="${RED}failed${NC}"
            else
                STATUS="${YELLOW}failed${NC}"
            fi
        else
            STATUS="${GREEN}ok${NC}"
        fi

        printf "%-4d %-60s %-15s\n" "${SEVERITY[$i]}" "${TEST_NAMES[$i]}" "$STATUS"

        if [ ! -z "${RESULT_MSGS[$i]}" ]; then
            if [ "${TEST_FAILDS[$i]}" = true ]; then
                if [ "${SEVERITY[$i]}" -ge 200 ]; then
                    echo -e "${RED}${RESULT_MSGS[$i]}${NC}"
                else
                     echo -e "${YELLOW}${RESULT_MSGS[$i]}${NC}"
                fi
            else
                echo -e "${GREEN}${RESULT_MSGS[$i]}${NC}"
            fi
        fi
    done

    # Act on Test Results
    MAX_SEVERITY=0
    for i in ${!SEVERITY[@]}; do
        # Maximum Severity of a failed test
        if [ "${TEST_FAILDS[$i]}" = true ]; then
            TEST_SEVERITY="${SEVERITY[$i]}"
            MAX_SEVERITY=$((MAX_SEVERITY>TEST_SEVERITY? MAX_SEVERITY : TEST_SEVERITY))
        fi
    done


    echo " "
    if [ "$MAX_SEVERITY" -gt 0 ]; then
        echo -e "${YELLOW}##################################  PREFLIGHT CHECK REPORT ##########################################${NC}"
    else
        echo -e "${GREEN}###################################  PREFLIGHT CHECK REPORT ###########################################${NC}"
    fi
    echo " "

    TERMINATE=false
    if [ "$MAX_SEVERITY" -ge 300 ]; then
        # 300-and growing
        echo -e "${RED}Problems with a very high severity have been found! ${NC}"
        echo -e "${RED}A continuation of this script is not possible.${NC}"
        echo -e "${RED}Please fix the failed tests first! ${NC}"
        #exit 1
        TERMINATE=true
    elif [ "$MAX_SEVERITY" -ge 200 ]; then
        # 200-299
        echo -e "${RED}Problems with a high severity have been found! ${NC}"
        echo -e "${RED}This will most probably lead to problems in the operation or even installation of the platform.${NC}"
        echo -e "${RED}Please consider fixing this problems before continuing, it is highly recommended.${NC}"
        TERMINATE=true
    elif [ "$MAX_SEVERITY" -ge 100 ]; then
        # 100-199
        echo -e "${YELLOW}Problems with a medium severity have been found! ${NC}"
        echo -e "${YELLOW}Since your system is out of the specified constraints for the platform, problems during operation or the installation can occur.${NC}"
        echo -e "${YELLOW}Please consider fixing this problems before continuing, it is highly recommended.${NC}"
        TERMINATE=true
    elif [ "$MAX_SEVERITY" -ge 1 ]; then
        # 1-99
        echo -e "${YELLOW}Problems with a low severity have been found! ${NC}"
        echo -e "${YELLOW}Please consider fixing this problems before continuing, it is highly recommended.${NC}"
    else
        echo -e "${GREEN}No major problems have been found! ${NC}"
    fi

    echo " "

    if [ "$TERMINATE" = "true" ]; then
        if [ ! "$QUIET" = "false" ] ; then
            while true; do
                read -e -p "Do you want to fix the problems before continuing? (Recommended)" -i " no" yn
                case $yn in
                    [Yy]* ) echo "${RED}exiting...${NC}" && exit 1; break;;
                    [Nn]* ) echo "${YELLOW}continuing (be aware that you leaving the supported path, its dangerous here watch your step!)${NC}"; break;;
                    * ) echo "Please answer yes or no.";;
                esac
            done
        else
            echo -e "${RED}Exiting since you run in quiet mode${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}################################  PREFLIGHT CHECKS COMPLETED  #########################################${NC}"
}

function create_report {
    # Dont abort report generation on error
    set +euf +o pipefail
    # Pipe output also to file
    exec > >(tee -ia "kaapana-report-$(date +'%Y-%m-%d').log")

    # https://stackoverflow.com/a/17366594
    trap_fn() {
    [[ $DEBUG && $BASH_COMMAND != "unset DEBUG" &&  $BASH_COMMAND != "--- "* ]] && \
        printf "[%s:%s] %s\n" "$BASH_SOURCE" "$LINENO" "$BASH_COMMAND"
    return 0 # do not block execution in extdebug mode
    }

    trap trap_fn DEBUG

    function --- {
        unset DEBUG
        echo ""
        echo ""
        echo "-----------------------------------------------"
        echo "$1"
        echo "-----------------------------------------------"
        DEBUG=1
    }
cat << "EOF"


                           .=#%@@@%#-                                 
                          .@@@@@@@@@@                                 
                     .::::*@@@@@@@@+      :+##*+=.                    
                 .+%@@@@@@#  -@@@-       *@@@@@@@@#:                  
                -@@@@@@@@@+   #@#       -@@@@@@@@@@@=.=#%*=           
                #@@@@@@@@#. :#@@@#=---=#@@@@@@@@@@@#+#@@@@@@*         
           .:::=@@@@@@@%- -%@@@@@@@@@@@+.   .-===-.   #@@@@@@%        
         +@@@@@@-:+@@@=  +@@@@@@@@@@@@=                +@@@@@@=       
       :@@@@@@@#   %@=   @@@@@@@@@@@@@=                 .#@@@#  =##=  
       %@@@@@@@=  =@@%.  +@@@@@@@@@@@@@+.    .:---.       +@%  :@@@@% 
       *@@@@@@= .#@@@@@=  -%@@@@@@@@##*#@@@@@@@@@@@@*.    .@#  :@@@@@*
 .*@@#. #@@@*. +@@@@@@@@%.  -%@@@=.      *@@@@@@@@@@@@-  .#@@+  %@@@@@
.@@@@@#  %@=  *@@@@@@@@@@*   .@@=         +@@@@@@@@@@@@ -@@@@@#..%@@@#
#@@@@@%  %@.  %@@@@@@@@@@*   -@@+          *@@@@@@@@@@@:@@@@@@@@  %@@.
%@@@@@= *@@%: +@@@@@@@@@@.  =@@@@*.         -%@@@@@@@%:=@@@@@@@@= .@- 
=@@@@=.%@@@@@+ =@@@@@@@*. -%@@@@@@@=          :=+**+-  .@@@@@@@@- :@. 
 .-:  %@@@@@@@+  :===-   +@@@@@@@@@@#             .::.  =@@@@@@#:*@@* 
     .@@@@@@@@%   :-:   .@@@@@@@@@@@@-         -#@@@@@@#-.-++=.*@@@@@-
      %@@@@@@@+ =@@@@@*..@@@@@@@@@@@@:        +@@@@@@@@@@%-   +@@@@@@+
       *@@@@@*  @@@@@@@% =@@@@@@@@@@#        .@@@@@@@@@@@@@@%@@@@@@@@=
        .---    +@@@@@@@  :#@@@@@@@@#:----.   @@@@@@@@@@@@+:.:#@@@@@% 
                 -#@@@*.     :---..%@@@@@@@%= :@@@@@@@@@@:     :#@%+  
                                   @@@@@@@@@@%  =#@@@@@@:             
                                  :@@@@@@@@@@@#   .-#@@*              
                                   #@@@@@@@@@@@*     +@%              
 | |/ /                                   +@@@@@@@@@@@%+--+@@@@*-           
 | ' / __ _  __ _ _ __   __ _ _ __   __ _  -+*#*+=-::+@@@@@@@@@@#          
 |  < / _` |/ _` | '_ \ / _` | '_ \ / _` |            :@@@@@@@@@@:         
 | . \ (_| | (_| | |_) | (_| | | | | (_| |             +@@@@@@@@=          
 |_|\_\__,_|\__,_| .__/ \__,_|_| |_|\__,_|              #@@@@@*. 
                 | |
  _   _          |_|       _____                       _
 | \ | |         | |      |  __ \                     | |
 |  \| | ___   __| | ___  | |__) |___ _ __   ___  _ __| |_ ___ _ __
 | . ` |/ _ \ / _` |/ _ \ |  _  // _ \ '_ \ / _ \| '__| __/ _ \ '__|
 | |\  | (_) | (_| |  __/ | | \ \  __/ |_) | (_) | |  | ||  __/ |
 |_| \_|\___/ \__,_|\___| |_|  \_\___| .__/ \___/|_|   \__\___|_|
                                     | |
                                     |_|
EOF
echo "Version: 0.1.4"
echo "Report created on $(date +'%Y-%m-%d')"

--- "Basics"
uptime
free

--- "Last Boot Log"
journalctl -b

--- "Pod Status"
microk8s.kubectl get pods -A

--- "External Internet Access"
ping -c3 -i 0.2 www.dkfz-heidelberg.de

--- "Check Registry"
openssl s_client -connect $CONTAINER_REGISTRY_URL:443

--- "Check Registry Credentials"
helm registry login -u $CONTAINER_REGISTRY_USERNAME -p $CONTAINER_REGISTRY_PASSWORD $CONTAINER_REGISTRY_URL

--- "Systemd Status"
systemd status

--- "Storage"
df -h

--- "Snaps"
snap list

--- "k8s Pods"
microk8s.kubectl get pods -A

--- "k8s Node Status"
microk8s.kubectl describe node

--- "GPU"
nvidia-smi

--- "END"
}

### MAIN programme body:

### Parsing command line arguments:
usage="$(basename "$0")

_Flag: --install-certs set new HTTPS-certificates for the platform
_Flag: --remove-all-images-ctr will delete all images from Microk8s (containerd)
_Flag: --remove-all-images-docker will delete all Docker images from the system
_Flag: --no-hooks will purge all kubernetes deployments and jobs as well as all helm charts. Use this if the undeployment fails or runs forever.
_Flag: --nuke-pods will force-delete all pods of the Kaapana deployment namespaces.
_Flag: --quiet, meaning non-interactive operation

_Argument: --username [Docker registry username]
_Argument: --password [Docker registry password]
_Argument: --port [Set main https-port]
_Argument: --chart-path [path-to-chart-tgz]
_Argument: --upload-tar [path-to-a-tarball]"

QUIET=NA

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in

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

        -d|--domain)
            DOMAIN="$2"
            echo -e "${GREEN}SET DOMAIN!${NC}";
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

        --no-hooks)
            echo -e "${YELLOW}Starting undeployment ...${NC}"
            NO_HOOKS="--no-hooks"
            echo -e "${YELLOW}Using --no-hooks${NC}"
            delete_deployment
            clean_up_kubernetes
            exit 0
        ;;

        --nuke-pods)
            while true; do
                read -e -p "Do you really want to nuke all pods? -> Not recommended!" -i " no" yn
                case $yn in
                    [Yy]* ) 
                    nuke_pods
                    delete_deployment
                    clean_up_kubernetes
                    break;;
                    [Nn]* ) echo "${YELLOW}Pods will be kept${NC}"; break;;
                    * ) echo "Please answer yes or no.";;
                esac
            done
            exit 0
        ;;

        --undeploy)
            delete_deployment
            exit 0
        ;;

        --re-deploy)
            delete_deployment
            deploy_chart
            exit 0
        ;;

        --report)
            create_report
            exit 0
        ;;

        *)    # unknown option
            echo -e "${RED}unknown parameter: $key ${NC}"
            echo -e "${YELLOW}$usage${NC}"
            exit 1
        ;;
    esac
done

preflight_checks

echo -e "${YELLOW}Get helm deployments...${NC}"
deployments=$(helm -n $HELM_NAMESPACE ls -a |cut -f1 |tail -n +2)
echo "Current deployments: " 
echo $deployments

if [[ $deployments == *"$PLATFORM_NAME"* ]] && [[ ! $QUIET = true ]];then
    echo -e "${YELLOW}$PLATFORM_NAME already deployed!${NC}"
    PS3='select option: '
    options=("Un- and Re-deploy" "Undeploy" "Quit")
    select opt in "${options[@]}"
    do
        case $opt in
            "Un- and Re-deploy")
                echo -e "${YELLOW}Starting Un- and Re-deployment ...${NC}"
                delete_deployment
                deploy_chart
                break
                ;;
            "Undeploy")
                echo -e "${YELLOW}Starting undeployment ...${NC}"
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
elif [[ $deployments == *"$PLATFORM_NAME"* ]] && [[ $QUIET = true ]];then
    echo -e "${RED}Project already deployed!${NC}"
    echo -e "${RED}abort.${NC}"
    exit 1

else
    echo -e "${GREEN}No previous deployment found -> deploy ${NC}"
    deploy_chart
fi
