#!/bin/bash
# Kaapana control helper: run `./kaapanactl.sh deploy|install|report [options]` to deploy the platform,
# prepare servers, or gather microk8s diagnostics without touching other scripts manually.
# if unusual home dir of user: sudo dpkg-reconfigure apparmor
set -euf -o pipefail

function main() {
    setup_environment
    local subcommand="help"

    if [[ $# -gt 0 ]]; then
        case "$1" in
            help|--help|-h)
                subcommand="help"
                shift
                ;;
            deploy|install|report|offline-gpu)
                subcommand="$1"
                shift
                ;;
            --*|-*)
                subcommand="deploy"
                ;;
            *)
                echo -e "${RED}Unknown command: $1${NC}"
                print_usage
                exit 1
                ;;
        esac
    fi

    case "$subcommand" in
        help)
            print_usage
            ;;
        deploy)
            deploy "$@"
            ;;
        install)
            server_installation "$@"
            ;;
        report)
            create_report
            ;;
        offline-gpu)
            install_gpu_operator "$(dirname "$0")"
            ;;
        *)
            print_usage
            exit 1
            ;;
    esac
}

function print_usage() {
    local script_name
    script_name="$(basename "$0")"
    cat <<EOF
Usage: $script_name <command> [options]

Commands:
  deploy               Deploy or manage the Kaapana platform.
  install              Run the server installation helper.
  report               Generate a microk8s state report without deploying.
  offline-gpu          Install the GPU Operator for offline environments.

Run '$script_name <command> --help' for command-specific options.
EOF
}

function prompt_required_value() {
    local var_name="$1"
    local prompt="$2"
    local secret="${3:-false}"
    local quiet_flag="${4:-false}"
    local current=""

    if [[ -n ${!var_name-} ]]; then
        current="${!var_name}"
    fi

    if [[ -n "$current" ]]; then
        return
    fi

    if [[ "$quiet_flag" == true ]]; then
        echo -e "${RED}${prompt} is required when running in quiet mode.${NC}"
        exit 1
    fi

    local value=""
    if [[ "$secret" == true ]]; then
        read -s -p "$prompt" value
        echo
    else
        read -p "$prompt" value
    fi

    if [[ -z "$value" ]]; then
        echo -e "${RED}A value is required for ${prompt}.${NC}"
        exit 1
    fi

    printf -v "$var_name" '%s' "$value"
}

function parse_chart_reference() {
    local ref="$1"
    ref="${ref#oci://}"

    if [[ -z "$ref" || "$ref" != *:* ]]; then
        echo -e "${RED}Chart reference must be in the form <registry>/<path>/<chart>:<version>. Got '$1'.${NC}"
        exit 1
    fi

    local registry_and_chart="${ref%:*}"
    local version="${ref##*:}"

    if [[ -z "$version" ]]; then
        echo -e "${RED}Chart reference is missing the version part after ':'.${NC}"
        exit 1
    fi

    local chart_name="${registry_and_chart##*/}"
    if [[ -z "$chart_name" || "$registry_and_chart" == "$chart_name" ]]; then
        echo -e "${RED}Chart reference must include a chart name (last segment after '/').${NC}"
        exit 1
    fi

    local registry_url="${registry_and_chart%/$chart_name}"
    if [[ -z "$registry_url" ]]; then
        echo -e "${RED}Unable to determine registry URL from chart reference '$1'.${NC}"
        exit 1
    fi

    PLATFORM_NAME="$chart_name"
    PLATFORM_VERSION="$version"
    CONTAINER_REGISTRY_URL="$registry_url"
    CHART_REFERENCE="$ref"

    echo -e "${GREEN}Using chart ${PLATFORM_NAME}:${PLATFORM_VERSION} from ${CONTAINER_REGISTRY_URL}${NC}"
}

function deploy() {

    PLATFORM_NAME="${PLATFORM_NAME:-}"
    PLATFORM_VERSION="${PLATFORM_VERSION:-}"
    CONTAINER_REGISTRY_URL="${CONTAINER_REGISTRY_URL:-}"
    CONTAINER_REGISTRY_USERNAME="${CONTAINER_REGISTRY_USERNAME:-}"
    CONTAINER_REGISTRY_PASSWORD="${CONTAINER_REGISTRY_PASSWORD:-}"
    CHART_REFERENCE="${CHART_REFERENCE:-}"
    PLAIN_HTTP="${PLAIN_HTTP:-false}"

    load_kaapana_config
    ### Parsing command line arguments:
    usage="$(basename "$0")

    _Flag: --undeploy undeploys the current platform
    _Flag: --no-hooks will purge all kubernetes deployments and jobs as well as all helm charts. Use this if the undeployment fails or runs forever.
    _Flag: --install-certs set new HTTPS-certificates for the platform
    _Flag: --remove-all-images-ctr will delete all images from Microk8s (containerd)
    _Flag: --remove-all-images-docker will delete all Docker images from the system
    _Flag: --nuke-pods will force-delete all pods of the Kaapana deployment namespaces.
    _Flag: --quiet, meaning non-interactive operation
    _Flag: --offline, using prebuilt tarball and chart (--chart-path required!)
    _Flag: --check-system, check health of all resources in kaapana-admin-chart and kaapana-platform-chart
    _Flag: --report, create a report of the state of the microk8s cluster
    _Flag: --plain-http, use insecure HTTP when talking to the registry (default HTTPS, use --no-plain-http to force it)

    _Argument: --chart-ref [registry/path/chart:version]
    _Argument: --platform-name [Helm chart name]
    _Argument: --platform-version [Helm chart version]
    _Argument: --registry-url [OCI registry URL]
    _Argument: --username [Docker registry username]
    _Argument: --password [Docker registry password]
    _Argument: --port [Set main https-port]
    _Argument: --chart-path [path-to-chart-tgz]
    _Argument: --import-images-tar [path-to-a-tarball]"

    QUIET=false

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

            --platform-name)
                PLATFORM_NAME="$2"
                echo -e "${GREEN}SET PLATFORM_NAME: $PLATFORM_NAME ${NC}"
                shift
                shift
            ;;

            --platform-version)
                PLATFORM_VERSION="$2"
                echo -e "${GREEN}SET PLATFORM_VERSION: $PLATFORM_VERSION ${NC}"
                shift
                shift
            ;;

            --registry-url)
                CONTAINER_REGISTRY_URL="$2"
                echo -e "${GREEN}SET CONTAINER_REGISTRY_URL: $CONTAINER_REGISTRY_URL ${NC}"
                shift
                shift
            ;;

            --chart)
                CHART_REFERENCE="$2"
                parse_chart_reference "$CHART_REFERENCE"
                shift
                shift
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

            --import-images-tar)
                TAR_PATH="$2"
                echo -e "${GREEN}SET TAR_PATH: $TAR_PATH !${NC}";
                import_container_images_tar
                exit 0
            ;;

            --quiet)
                QUIET=true
                shift # past argument
            ;;

            --offline)
                OFFLINE_MODE=true
                echo -e "${GREEN}Deploying in offline mode!${NC}"
                shift # past argument
            ;;

            --plain-http)
                PLAIN_HTTP=true
                echo -e "${YELLOW}Using insecure plain HTTP for registry access.${NC}"
                shift
            ;;

            --no-migration)
                MIGRATION_ENABLED=false
                echo -e "${YELLOW}Migration disabled via CLI (--no-migration).${NC}"
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

            --check-system)
                check_system kaapana-admin-chart default
                check_system kaapana-platform-chart admin
                check_system project-admin admin
                exit 0
            ;;

            *)    # unknown option
                echo -e "${RED}unknown parameter: $key ${NC}"
                echo -e "${YELLOW}$usage${NC}"
                exit 1
            ;;


        esac
    done

    if [[ -z "$PLATFORM_NAME" || -z "$PLATFORM_VERSION" || -z "$CONTAINER_REGISTRY_URL" ]]; then
        prompt_required_value CHART_REFERENCE "Enter the kaapana chart (registry/path/chart:version): " false "$QUIET"
        parse_chart_reference "$CHART_REFERENCE"
    fi

    prompt_required_value CONTAINER_REGISTRY_USERNAME "Enter the container registry username: " false "$QUIET"
    prompt_required_value CONTAINER_REGISTRY_PASSWORD "Enter the container registry password: " true "$QUIET"

    script_name=`basename "$0"`

    if [ -z ${http_proxy+x} ] || [ -z ${https_proxy+x} ]; then
        http_proxy=""
        https_proxy=""
    fi
    export HELM_EXPERIMENTAL_OCI=1
    HELM_EXECUTABLE="${HELM_EXECUTABLE:-helm}"

    if [ ! -z $INSTANCE_UID ]; then
        echo ""
        echo "Setting INSTANCE_UID: $INSTANCE_UID namespaces ..."
        SERVICES_NAMESPACE="$INSTANCE_UID-$SERVICES_NAMESPACE"
        # ADMIN_NAMESPACE="$INSTANCE_UID-$ADMIN_NAMESPACE"
        EXTENSIONS_NAMESPACE="$INSTANCE_UID-$EXTENSIONS_NAMESPACE"
        HELM_NAMESPACE="$INSTANCE_UID-$HELM_NAMESPACE"

        FAST_DATA_DIR="$FAST_DATA_DIR-$INSTANCE_UID"
        SLOW_DATA_DIR="$SLOW_DATA_DIR-$INSTANCE_UID"

        INCLUDE_REVERSE_PROXY=true
    fi
    echo ""
    echo "HELM_NAMESPACE:       $HELM_NAMESPACE "
    echo "ADMIN_NAMESPACE:      $ADMIN_NAMESPACE "
    echo "SERVICES_NAMESPACE:   $SERVICES_NAMESPACE "
    echo "EXTENSIONS_NAMESPACE: $EXTENSIONS_NAMESPACE "
    echo ""
    echo "FAST_DATA_DIR: $FAST_DATA_DIR "
    echo "SLOW_DATA_DIR: $SLOW_DATA_DIR "
    echo ""

    if command -v nvidia-smi &> /dev/null && nvidia-smi
    then
        echo "${GREEN}Nvidia GPU detected!${NC}"
        GPU_SUPPORT=true
    else
        echo "${YELLOW}No GPU detected...${NC}"
        GPU_SUPPORT=false
    fi

    preflight_checks

    echo -e "${YELLOW}Get helm deployments...${NC}"
    deployments=$(
    # Helm 3 vs Helm 4:
    # - Helm 3 needs `helm list -a` to show all releases (no --no-headers flag).
    # - Helm 4 removed `-a` and `helm list` already lists all statuses by default.
    #   See: https://helm.sh/docs/v3/helm/helm_list/ and https://helm.sh/docs/helm/helm_list/
    #
    # Try Helm 3 syntax first; if it fails (e.g. unknown flag -a), fall back to Helm 4 syntax.
    $HELM_EXECUTABLE -n "$HELM_NAMESPACE" ls --short -a 2>/dev/null || \
    $HELM_EXECUTABLE -n "$HELM_NAMESPACE" ls --short --no-headers 2>/dev/null
    )
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
}

function server_installation() {
    echo "TODO: Transfer server installation functionality here."
}

install_gpu_operator() {
  local script_dir="$1"

  if [[ -z "${script_dir}" ]]; then
    echo "install_gpu_operator: missing required argument: script_dir" >&2
    return 1
  fi

  # Constants
  local chart_name="gpu-operator"
  local chart_version="v25.3.0"
  local helm="/snap/bin/helm"
  local containerd_socket="/var/snap/microk8s/common/run/containerd.sock"
  local containerd_toml="/var/snap/microk8s/current/args/containerd-template.toml"

  local chart_path="${script_dir%/}/gpu-operator.tgz"

  if [[ ! -f "${chart_path}" ]]; then
    echo "install_gpu_operator: chart not found at ${chart_path}" >&2
    return 1
  fi

  # Match Python: only distinguish by presence of nvidia-smi (OSError equivalent)
  local driver
  if command -v nvidia-smi >/dev/null 2>&1; then
    driver="host"
  else
    driver="operator"
  fi

  local driver_enabled
  if [[ "${driver}" == "operator" ]]; then
    driver_enabled="true"
  else
    driver_enabled="false"
  fi

  # Feed JSON values to Helm via stdin (equivalent to -f - in the Python script)
  cat <<EOF | "${helm}" install "${chart_name}" "${chart_path}" \
    --version="${chart_version}" \
    --create-namespace \
    --namespace="${chart_name}-resources" \
    -f -
{
  "operator": {
    "defaultRuntime": "containerd"
  },
  "driver": {
    "enabled": "${driver_enabled}"
  },
  "toolkit": {
    "enabled": "true",
    "env": [
      { "name": "CONTAINERD_CONFIG", "value": "${containerd_toml}" },
      { "name": "CONTAINERD_SOCKET", "value": "${containerd_socket}" },
      { "name": "CONTAINERD_SET_AS_DEFAULT", "value": "1" }
    ]
  }
}
EOF
}


function setup_environment {
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
}

function load_kaapana_config {
    ######################################################
    # Deployment configuration
    ######################################################

    # dev-mode -> containers will always be re-downloaded after pod-restart
    DEV_MODE=True
    GPU_SUPPORT=False
    # Adjust enable nvidia command if using GPU Operator below v25.10.0+
    GPU_OPERATOR_VERSION="v25.10.0"
    PREFETCH_EXTENSIONS=false
    CHART_PATH=""
    NO_HOOKS=""
    ENABLE_NFS=false
    OFFLINE_MODE=false

    INSTANCE_UID=""
    SERVICES_NAMESPACE="services"
    ADMIN_NAMESPACE="admin"
    EXTENSIONS_NAMESPACE="extensions"
    HELM_NAMESPACE="default"

    OIDC_CLIENT_SECRET=$(echo $RANDOM | md5sum | base64 | head -c 32)

    INCLUDE_REVERSE_PROXY=false

    ######################################################
    # Resource configurations
    ######################################################

    # Memory percentages for PACS, Airflow, and OpenSearch.
    PACS_PERCENT="30"
    AIRFLOW_PERCENT="50"
    OPENSEARCH_PERCENT="20"
    TOTAL_PERCENT=$((PACS_PERCENT + AIRFLOW_PERCENT + OPENSEARCH_PERCENT))

    # Get allocatable RAM (70% of total free memory)
    TOTAL_MEMORY=$(free -m | awk '/^Mem:/{print $2}')
    ALLOCATABLE_MEMORY=$((TOTAL_MEMORY * 70 / 100))

    # Set max memory limits for components
    PACS_MEMORY_LIMIT=$((ALLOCATABLE_MEMORY * PACS_PERCENT / TOTAL_PERCENT))
    AIRFLOW_MEMORY_LIMIT=$((ALLOCATABLE_MEMORY * AIRFLOW_PERCENT / TOTAL_PERCENT))
    OPENSEARCH_MEMORY_LIMIT=$((ALLOCATABLE_MEMORY * OPENSEARCH_PERCENT / TOTAL_PERCENT))

    # Set memory min requests (1/3 of limit)
    PACS_MEMORY_REQUEST=$((PACS_MEMORY_LIMIT / 3))
    AIRFLOW_MEMORY_REQUEST=$((AIRFLOW_MEMORY_LIMIT / 3))
    OPENSEARCH_MEMORY_REQUEST=$((OPENSEARCH_MEMORY_LIMIT / 3))

    ######################################################
    # Individual platform configuration
    ######################################################
    CREDENTIALS_MINIO_USERNAME="kaapanaminio"
    CREDENTIALS_MINIO_PASSWORD="Kaapana2020"

    GRAFANA_USERNAME="admin"
    GRAFANA_PASSWORD="admin"

    KEYCLOAK_ADMIN_USERNAME="admin"
    KEYCLOAK_ADMIN_PASSWORD="Kaapana2020" #  Minimum policy for production: 1 specialChar + 1 upperCase + 1 lowerCase and 1 digit + min-length = 8

    FAST_DATA_DIR="/home/kaapana" # Directory on the server, where stateful application-data will be stored (databases, processing tmp data etc.)
    SLOW_DATA_DIR="/home/kaapana" # Directory on the server, where the DICOM images will be stored (can be slower)

    HTTP_PORT="80"      # -> has to be 80
    HTTPS_PORT="443"    # HTTPS port
    DICOM_PORT="11112"  # configure DICOM receiver port

    SMTP_HOST=""
    SMTP_PORT="0"
    EMAIL_ADDRESS_SENDER=""
    SMTP_USERNAME=""
    SMTP_PASSWORD=""

    VERSION_IMAGE_COUNT="20"
    DEPLOYMENT_TIMESTAMP=`date  --iso-8601=seconds`
    MOUNT_POINTS_TO_MONITOR=""

    INSTANCE_NAME=""
}

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
        echo -e "${YELLOW}Get Server IP ...${NC}";
        SERVER_IP=$(hostname -I | awk -F ' ' '{print $1}')
        echo -e "${YELLOW}SERVER_IP: $SERVER_IP${NC}";
        echo -e "${YELLOW}NS lookup DOMAIN ...${NC}";
        # get nslookup result, use || true to ensure script doesn't exit immediately is cmd fails
        NSLOOKUP_RESULT=$(nslookup "$SERVER_IP" || true)
        if [[ -z "$NSLOOKUP_RESULT" || "$NSLOOKUP_RESULT" == *"server can't find"* ]]; then
            echo -e "NS lookup failed, could not determine DOMAIN from SERVER_IP. Run the script with explicit domain name: ./deploy_platform.sh --domain <domain-name>"
            exit 1
        fi
        DOMAIN=$(echo "$NSLOOKUP_RESULT" | head -n 1 | awk -F '= ' '{print $2}')
        DOMAIN=${DOMAIN%.*}
        echo -e "${YELLOW}DOMAIN: $DOMAIN${NC}";
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
    fi
}

function delete_deployment {
    echo -e "${YELLOW}Undeploy releases${NC}"
    for namespace in $ADMIN_NAMESPACE $HELM_NAMESPACE; do
        $HELM_EXECUTABLE -n $namespace ls --deployed --failed --pending --superseded --uninstalling --date --reverse | awk 'NR > 1 { print  "-n "$2, $1}' | xargs -I % sh -c "$HELM_EXECUTABLE -n $namespace uninstall ${NO_HOOKS} --wait --timeout 5m30s %; sleep 2"
    done

    echo -e "${YELLOW}Waiting until everything is terminated ...${NC}"
    WAIT_UNINSTALL_COUNT=100
    for idx in $(seq 0 $WAIT_UNINSTALL_COUNT)
    do
        sleep 3
        if [ "$idx" -eq 2 ]; then
            echo "Deleting helm charts in 'uninstalling' state with --no-hooks"
            $HELM_EXECUTABLE -n $namespace ls --uninstalling | awk 'NR > 1 { print  "-n "$2, $1}' | xargs -I % sh -c "$HELM_EXECUTABLE -n $namespace uninstall --no-hooks --wait --timeout 5m30s %; sleep 2"
        fi
        DEPLOYED_NAMESPACES=$(/bin/bash -i -c "kubectl get namespaces | grep -E --line-buffered '$EXTENSIONS_NAMESPACE' | cut -d' ' -f1")
        TERMINATING_PODS=$(/bin/bash -i -c "kubectl get pods --all-namespaces | grep -E --line-buffered 'Terminating' | cut -d' ' -f1")
        echo -e ""
        UNINSTALL_TEST=$DEPLOYED_NAMESPACES$TERMINATING_PODS
        if [ -z "$UNINSTALL_TEST" ]; then
            break
        else
            echo -e "${YELLOW}Waiting for $TERMINATING_PODS $DEPLOYED_NAMESPACES ${NC}"
        fi
    done
    if [ ! "$QUIET" = "true" ];then
        while true; do
            read -e -p "Do you also want to remove all Persistent Volumes in the cluster (kubectl delete pv --all)?" -i " yes" yn
            case $yn in
                [Yy]* ) echo -e "${GREEN}Removing all pvs from cluster ...${NC}" && microk8s.kubectl delete pv --all; break;;
                [Nn]* ) echo -e "${YELLOW}Skipping pv removal ...{NC}"; break;;
                * ) echo "Please answer yes or no.";;
            esac
        done
    else
        echo -e "${YELLOW}QUIET-MODE active!${NC}"
        echo -e "${GREEN}Removing all pvs from cluster ...${NC}"
        microk8s.kubectl delete pv --all
    fi

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
    for namespace in $EXTENSIONS_NAMESPACE $SERVICES_NAMESPACE $ADMIN_NAMESPACE $HELM_NAMESPACE; do
        echo "${RED}Deleting all pods from namespaces: $namespace ...${NC}";
        for mypod in $(microk8s.kubectl get pods -n $namespace -o jsonpath="{.items[*].metadata.name}");
        do
            echo "${RED}Deleting: $mypod ${NC}";
            microk8s.kubectl delete pod -n $namespace $mypod --grace-period=0 --force
        done
    done
}

function clean_up_kubernetes {
    for n in $EXTENSIONS_NAMESPACE; # $HELM_NAMESPACE;
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

function import_container_images_tar {
    echo "${RED}Importing the images from the tar, this might take a long time -> please be patient and wait.${NC}"
    microk8s.ctr images import $TAR_PATH
    echo "${GREEN}Finished image upload! You should now be able to deploy the platform by specifying the chart path.${NC}"
}

function run_migration_chart() {
    local FROM_VERSION="$1"
    local TO_VERSION="$2"

    echo -e "${YELLOW}Deploying migration chart: $FROM_VERSION -> $TO_VERSION${NC}"

    WORKDIR=$(mktemp -d)
    tar -xzf "$CHART_PATH" -C "$WORKDIR"

    MIGRATION_CHART_PATH="$WORKDIR/$PLATFORM_NAME/charts/migration-chart"
    if [[ ! -d "$MIGRATION_CHART_PATH" ]]; then
        echo -e "${RED}Migration chart not found inside chart package!${NC}"
        exit 1
    fi

    # Build helm command with optional --plain-http flag
    HELM_CMD="$HELM_EXECUTABLE -n $HELM_NAMESPACE upgrade --install"
    if [ "$PLAIN_HTTP" = true ]; then
        HELM_CMD="$HELM_CMD --plain-http"
    fi

    $HELM_CMD kaapana-migration "$MIGRATION_CHART_PATH" \
        --set-string global.credentials_registry_username="$CONTAINER_REGISTRY_USERNAME" \
        --set-string global.credentials_registry_password="$CONTAINER_REGISTRY_PASSWORD" \
        --set-string global.fast_data_dir="$FAST_DATA_DIR" \
        --set-string global.slow_data_dir="$SLOW_DATA_DIR" \
        --set-string global.pull_policy_images="$PULL_POLICY_IMAGES" \
        --set-string global.registry_url="$CONTAINER_REGISTRY_URL" \
        --set-string global.kaapana_build_version="$PLATFORM_VERSION" \
        --set-string global.from_version="$FROM_VERSION" \
        --set-string global.to_version="$TO_VERSION"

    # Wait for migration job to finish
    local JOB_NAME="migration"
    local NAMESPACE="migration"
    local TIMEOUT=180
    local INTERVAL=5
    local ELAPSED=0

    cleanup() {
        echo -e "${YELLOW}Cleaning up migration helm chart...${NC}"
        $HELM_EXECUTABLE uninstall "kaapana-migration" -n "$HELM_NAMESPACE" || true
    }

    echo -e "${YELLOW}Waiting for migration job $JOB_NAME to complete...${NC}"
        while true; do
        local SUCCEEDED=$(microk8s.kubectl get job "$JOB_NAME" -n "$NAMESPACE" -o jsonpath='{.status.succeeded}')
        local FAILED=$(microk8s.kubectl get job "$JOB_NAME" -n "$NAMESPACE" -o jsonpath='{.status.failed}')

        if [[ "${SUCCEEDED:-0}" -ge 1 ]]; then
            echo -e "${GREEN}Migration job completed successfully!${NC}"
            PODS=$(microk8s.kubectl get pods -n "$NAMESPACE" -l job-name="$JOB_NAME" -o name)
            for pod in $PODS; do
                microk8s.kubectl logs "$pod" -n "$NAMESPACE"
            done
            cleanup
            break
        elif [[ "${FAILED:-0}" -ge 1 ]]; then
            echo -e "${RED}Migration job failed!${NC}"
            PODS=$(microk8s.kubectl get pods -n "$NAMESPACE" -l job-name="$JOB_NAME" -o name)
            for pod in $PODS; do
                microk8s.kubectl logs "$pod" -n "$NAMESPACE"
            done

            POD=$(microk8s.kubectl get pods -n "$NAMESPACE" -l job-name="$JOB_NAME" -o jsonpath='{.items[*].metadata.name}')
            microk8s.kubectl logs "$POD" -n "$NAMESPACE"
            cleanup
            exit 1
        fi

        sleep "$INTERVAL"
        ELAPSED=$((ELAPSED + INTERVAL))
        if [[ $ELAPSED -ge $TIMEOUT ]]; then
            echo -e "${RED}Migration job did not complete within ${TIMEOUT}s${NC}"
            exit 1
        fi
    done
}

function prompt_user_backup() {
    echo -e "${YELLOW}Please BACKUP your data directory first${NC}"
    echo "   cp -a $FAST_DATA_DIR /path/to/fast/backup"
    echo "   cp -a $SLOW_DATA_DIR /path/to/slow/backup"
    echo
    while true; do
        read -p "Proceed with migration? (yes/no): " answer
        case "$answer" in
            [Yy][Ee][Ss]|[Yy])
                echo "✅ Proceeding with migration..."
                break
                ;;
            [Nn][Oo]|[Nn])
                echo "❌ Aborting migration."
                exit 1
                ;;
            *)
                echo "Please type 'yes' or 'no'."
                ;;
        esac
    done
}

function migrate() {
    VERSION_FILE="$FAST_DATA_DIR/version"

    echo "${YELLOW}Checking ${VERSION_FILE} status...${NC}"

    if [[ ! -d "$FAST_DATA_DIR" || -z "$(ls -A "$FAST_DATA_DIR" 2>/dev/null)" ]]; then
        echo "${GREEN}Fresh installation detected. Running migration chart to create version file.${NC}"
         # Just creating a version file. Could be handled somewhere else, in the kaapana-admin-chart or whatever.)
        run_migration_chart "fresh" "$PLATFORM_VERSION"

    elif [[ -f "$VERSION_FILE" ]]; then
        CURRENT_VERSION=$(cat "$VERSION_FILE")
        echo "Found version: $CURRENT_VERSION"

        if [[ "$CURRENT_VERSION" == "$PLATFORM_VERSION" ]]; then
            echo "${GREEN}Version matches ($PLATFORM_VERSION). Skipping migration.${NC}"
        else
            echo "${YELLOW}Version mismatch: current=$CURRENT_VERSION, deploy=$PLATFORM_VERSION.${NC}"

            # Extract major.minor
            cur_major=$(echo "$CURRENT_VERSION" | cut -d. -f1)
            cur_minor=$(echo "$CURRENT_VERSION" | cut -d. -f2)
            dep_major=$(echo "$PLATFORM_VERSION" | cut -d. -f1)
            dep_minor=$(echo "$PLATFORM_VERSION" | cut -d. -f2)

            echo "${YELLOW}Version change detected: $CURRENT_VERSION -> $PLATFORM_VERSION.${NC}"
            prompt_user_backup
            run_migration_chart "$CURRENT_VERSION" "$PLATFORM_VERSION"
        fi

    elif [[ -d "$FAST_DATA_DIR" && -n "$(ls -A "$FAST_DATA_DIR")" ]]; then
        echo "${YELLOW}No version file and directory is not empty!${NC}"
        echo "Options:"
        echo "  1. Let migration-chart autodetect version using $FAST_DATA_DIR/extensions/kaapana-platform-chart-<version>.tgz"
        echo "  2. Exit to manually create $VERSION_FILE with correct version and rerun the deploy script."
        read -p "Choose option (1/2): " choice
        if [[ "$choice" == "1" ]]; then
            prompt_user_backup
            run_migration_chart "autodetect" "$PLATFORM_VERSION"
        else
            echo "${RED}Please create the version file manually and rerun.${NC}"
            exit 1
        fi
    else
        echo "Unexpected state. Please check $FAST_DATA_DIR."
        exit 1
    fi
}

function deploy_chart {
    if [ -z "$CONTAINER_REGISTRY_URL" ]; then
        echo "${RED}CONTAINER_REGISTRY_URL needs to be set! -> please adjust the deploy_platform.sh script!${NC}"
        echo "${RED}ABORT${NC}"
        exit 1
    fi

    if [ "${OFFLINE_MODE,,}" == true ] && [ -z "$CHART_PATH" ]; then
        echo "${RED}ERROR: CHART_PATH needs to be set when in OFFLINE_MODE!${NC}"
        exit 1
    fi

    get_domain

    if [ -z "$INSTANCE_NAME" ]; then
        INSTANCE_NAME=$DOMAIN
        echo "${YELLOW}No INSTANCE_NAME is set, setting it to $DOMAIN!${NC}"
    fi

    if [ "${GPU_SUPPORT,,}" == true ];then
        echo -e "${GREEN} -> GPU found ...${NC}"
    else
        if [ ! "$QUIET" = "true" ];then
            while true; do
                read -e -p "No Nvidia GPU detected - Enable GPU support anyway?" -i " no" yn
                case $yn in
                    [Yy]* ) echo -e "${GREEN}ENABLING GPU SUPPORT${NC}" && GPU_SUPPORT=true; break;;
                    [Nn]* ) echo -e "${YELLOW}SET NO GPU SUPPORT${NC}" && GPU_SUPPORT=false; break;;
                    * ) echo "Please answer yes or no.";;
                esac
            done
        else
            echo -e "${YELLOW}QUIET-MODE active!${NC}"
        fi
    fi

    echo -e "${YELLOW}GPU_SUPPORT: $GPU_SUPPORT ${NC}"
    if [ "${GPU_SUPPORT,,}" == true ];then
        echo -e "-> enabling GPU in Microk8s ..."
        if [[ $deployments == *"gpu-operator"* ]];then
            echo -e "-> gpu-operator chart already exists"
        else
            if [ "${OFFLINE_MODE,,}" == true ];then
                SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
                OFFLINE_ENABLE_GPU_PATH=$SCRIPT_DIR/offline_enable_gpu.py
                [ -f $OFFLINE_ENABLE_GPU_PATH ] && echo "${GREEN}$OFFLINE_ENABLE_GPU_PATH exists ... ${NC}" || (echo "${RED}$OFFLINE_ENABLE_GPU_PATH does not exist -> exit ${NC}" && exit 1)
                python3 $OFFLINE_ENABLE_GPU_PATH --script-dir $SCRIPT_DIR
                if [ $? -eq 0 ]; then
                    echo "Offline GPU enabled!"
                else
                    echo "Offline GPU deployment failed!"
                    exit 1
                fi
            else

                microk8s enable nvidia --gpu-operator-driver host --gpu-operator-version $GPU_OPERATOR_VERSION \
                    --gpu-operator-set toolkit.env[3].name=RUNTIME_CONFIG_SOURCE --gpu-operator-set toolkit.env[3].value='file=/var/snap/microk8s/current/args/containerd.toml'
            fi
        fi
    fi

    if [ "${DEV_MODE,,}" == true ]; then
        KAAPANA_INIT_PASSWORD="kaapana"
    else
        KAAPANA_INIT_PASSWORD="Kaapana2020!"
    fi

    if [ "${OFFLINE_MODE,,}" == true ] || [ "${DEV_MODE,,}" == false ]; then
        PULL_POLICY_IMAGES="IfNotPresent"
    else
        PULL_POLICY_IMAGES="Always"
    fi

    # configmap kube-public/local-registry-hosting is used by EDK if installed inside Kaapana, therefore should not already exist
    echo "${YELLOW}Removing configmap kube-public/local-registry-hosting if exists...${NC}"
    microk8s.kubectl delete configmap -n kube-public local-registry-hosting --ignore-not-found=true

    if [ ! -z "$CHART_PATH" ]; then # Note: OFFLINE_MODE requires CHART_PATH
        echo -e "${YELLOW}We assume that that all images are already presented inside the microk8s.${NC}"
        echo -e "${YELLOW}Images are uploaded either with a previous deployment from a docker registry or uploaded from a tar or directly uploaded during building the platform.${NC}"

        if [ $(basename "$CHART_PATH") != "$PLATFORM_NAME-$PLATFORM_VERSION.tgz" ]; then
            echo "${RED} Version of chart_path $CHART_PATH differs from PROJECT_NAME: $PLATFORM_NAME and PLATFORM_VERSION: $PLATFORM_VERSION in the deployment script.${NC}"
            exit 1
        fi

        if [ ! "$QUIET" = "true" ];then
            while true; do
            echo -e "${YELLOW}You are deploying the platform in offline mode!${NC}"
                read -p "${YELLOW}Please confirm that you are sure that all images are present in microk8s (yes/no): ${NC}" yn
                    case $yn in
                        [Yy]* ) echo "${GREEN}Confirmed${NC}"; break;;
                        [Nn]* ) echo "${RED}Cancel${NC}"; exit;;
                        * ) echo "Please answer yes or no.";;
                    esac
            done
        else
            echo -e "${GREEN}QUIET: true -> SKIP USER INPUT ${NC}";
        fi

        echo -e "${YELLOW}Checking available images with version: $PLATFORM_VERSION ${NC}"
        set +e
        PRESENT_IMAGE_COUNT=$( microk8s.ctr images ls | grep $PLATFORM_VERSION | wc -l)
        set -e
        echo -e "${YELLOW}PRESENT_IMAGE_COUNT: $PRESENT_IMAGE_COUNT ${NC}"
        if [ "$PRESENT_IMAGE_COUNT" -lt "$VERSION_IMAGE_COUNT" ];then
            echo -e "${RED}There are only $PRESENT_IMAGE_COUNT present with the version $PLATFORM_VERSION - there seems to be an issue. ${NC}"
            exit 1
        else
            echo -e "${GREEN}PRESENT_IMAGE_COUNT: OK ${NC}"
        fi

        PREFETCH_EXTENSIONS=false
        CONTAINER_REGISTRY_USERNAME=""
        CONTAINER_REGISTRY_PASSWORD=""
    else
        echo "${YELLOW}Helm login registry...${NC}"
        check_credentials
        echo "${GREEN}Pulling platform chart from registry...${NC}"
        SCRIPT_PATH=$(dirname "$(realpath $0)")
        pull_chart "$PLATFORM_NAME" "$PLATFORM_VERSION" "$SCRIPT_PATH"
        CHART_PATH="$SCRIPT_PATH/$PLATFORM_NAME-$PLATFORM_VERSION.tgz"
    fi

    # Kubernetes API endpoint
    INTERNAL_CIDR=$(microk8s.kubectl get endpoints kubernetes -n default -o jsonpath="{.subsets[0].addresses[0].ip}/32")
    # Server IP
    if [[ "$DOMAIN" =~ ^(([1-9]?[0-9]|1[0-9][0-9]|2([0-4][0-9]|5[0-5]))\.){3}([1-9]?[0-9]|1[0-9][0-9]|2([0-4][0-9]|5[0-5]))$ ]]; then
        # external ip can differ from local ip, must be reachable due to keycloak (only in ip deployments)
        INTERNAL_CIDR="$DOMAIN/32,$INTERNAL_CIDR"
    fi
    SERVER_IP=$(hostname -I | awk -F ' ' '{print $1}')
    INTERNAL_CIDR="$SERVER_IP/32,$INTERNAL_CIDR"
    # MicroK8s https://microk8s.io/docs/change-cidr
    INTERNAL_CIDR="10.152.183.0/24,10.1.0.0/16,$INTERNAL_CIDR"


    echo "${GREEN}Checking for version difference and migration options...${NC}"
    migrate

    echo "${GREEN}Deploying $PLATFORM_NAME:$PLATFORM_VERSION${NC}"
    echo "${GREEN}CHART_PATH $CHART_PATH${NC}"

    # Build helm command with optional --plain-http flag
    HELM_INSTALL_CMD="$HELM_EXECUTABLE -n $HELM_NAMESPACE install --create-namespace"
    if [ "$PLAIN_HTTP" = true ]; then
        HELM_INSTALL_CMD="$HELM_INSTALL_CMD --plain-http"
    fi

    $HELM_INSTALL_CMD $CHART_PATH \
    --set-string global.base_namespace="base" \
    --set-string global.credentials_registry_username="$CONTAINER_REGISTRY_USERNAME" \
    --set-string global.credentials_registry_password="$CONTAINER_REGISTRY_PASSWORD" \
    --set-string global.credentials_minio_username="$CREDENTIALS_MINIO_USERNAME" \
    --set-string global.credentials_minio_password="$CREDENTIALS_MINIO_PASSWORD" \
    --set-string global.credentials_grafana_username="$GRAFANA_USERNAME" \
    --set-string global.credentials_grafana_password="$GRAFANA_PASSWORD" \
    --set-string global.credentials_keycloak_admin_username="$KEYCLOAK_ADMIN_USERNAME" \
    --set-string global.credentials_keycloak_admin_password="$KEYCLOAK_ADMIN_PASSWORD" \
    --set-string global.dicom_port="$DICOM_PORT" \
    --set-string global.fast_data_dir="$FAST_DATA_DIR" \
    --set-string global.services_namespace=$SERVICES_NAMESPACE \
    --set-string global.extensions_namespace=$EXTENSIONS_NAMESPACE \
    --set-string global.admin_namespace=$ADMIN_NAMESPACE \
    --set global.gpu_support=$GPU_SUPPORT \
    --set-string global.helm_namespace="$ADMIN_NAMESPACE" \
    --set global.enable_nfs=$ENABLE_NFS \
    --set global.oidc_client_secret=$OIDC_CLIENT_SECRET \
    --set global.include_reverse_proxy=$INCLUDE_REVERSE_PROXY \
    --set-string global.home_dir="$HOME" \
    --set-string global.hostname="$DOMAIN" \
    --set-string global.http_port="$HTTP_PORT" \
    --set-string global.https_port="$HTTPS_PORT" \
    --set global.internalCidrs="{$INTERNAL_CIDR}" \
    --set-string squid-proxy.upstreamHttpProxy="$http_proxy" \
    --set-string squid-proxy.upstreamHttpsProxy="$https_proxy" \
    --set global.offline_mode=$OFFLINE_MODE \
    --set global.prefetch_extensions=$PREFETCH_EXTENSIONS \
    --set-string global.pull_policy_images="$PULL_POLICY_IMAGES" \
    --set-string global.pull_policy_jobs="$PULL_POLICY_IMAGES" \
    --set-string global.pull_policy_pods="$PULL_POLICY_IMAGES" \
    --set-string global.registry_url="$CONTAINER_REGISTRY_URL" \
    --set-string global.release_name="$PLATFORM_NAME" \
    --set-string global.deployment_timestamp="$DEPLOYMENT_TIMESTAMP" \
    --set-string global.mount_points_to_monitor="$MOUNT_POINTS_TO_MONITOR" \
    --set-string global.slow_data_dir="$SLOW_DATA_DIR" \
    --set-string global.instance_uid="$INSTANCE_UID" \
    --set-string global.instance_name="$INSTANCE_NAME" \
    --set global.dev_mode=$DEV_MODE \
    --set-string global.kaapana_init_password="$KAAPANA_INIT_PASSWORD" \
    --set-string global.pacs_memory_limit="$PACS_MEMORY_LIMIT" \
    --set-string global.airflow_memory_limit="$AIRFLOW_MEMORY_LIMIT" \
    --set-string global.opensearch_memory_limit="$OPENSEARCH_MEMORY_LIMIT" \
    --set-string global.pacs_memory_request="$PACS_MEMORY_REQUEST" \
    --set-string global.airflow_memory_request="$AIRFLOW_MEMORY_REQUEST" \
    --set-string global.opensearch_memory_request="$OPENSEARCH_MEMORY_REQUEST" \
    --set-string global.smtp_host="$SMTP_HOST" \
    --set-string global.smtp_port="$SMTP_PORT" \
    --set-string global.smtp_username="$SMTP_USERNAME" \
    --set-string global.smtp_password="$SMTP_PASSWORD" \
    --set-string global.email_address_sender="$EMAIL_ADDRESS_SENDER" \
    --name-template "$PLATFORM_NAME"

    # In case of timeout-issues in kube helm increase the default timeouts by setting
    # --set kube-helm-chart.timeouts.helmInstallTimeout=45 \
    # --set kube-helm-chart.timeouts.helmDeletionTimeout=60 \

    # pull_policy_jobs and pull_policy_pods only there for backward compatibility as of version 0.2.0
    if [ ! -z "$CONTAINER_REGISTRY_USERNAME" ] && [ ! -z "$CONTAINER_REGISTRY_PASSWORD" ]; then
        rm $CHART_PATH
    fi

    print_deployment_done
    update_coredns_rewrite
    CONTAINER_REGISTRY_USERNAME=""
    CONTAINER_REGISTRY_PASSWORD=""
}

function pull_chart {
    local chart_name=$1
    local chart_version=$2
    local dest_dir=$3

    MAX_RETRIES=30
    i=1
    while [ $i -le $MAX_RETRIES ];
    do
        echo -e "${YELLOW}Pulling chart: ${CONTAINER_REGISTRY_URL}/${chart_name} with version ${chart_version} ${NC}"
        $HELM_EXECUTABLE pull --plain-http oci://${CONTAINER_REGISTRY_URL}/${chart_name} \
            --version ${chart_version} -d ${dest_dir} \
            && break \
            || ( echo -e "${RED}Failed -> retry${NC}" && sleep 1 )
        ((i++))
    done

    if [ ! -f "${dest_dir}/${chart_name}-${chart_version}.tgz" ]; then
        echo -e "${RED}Could not pull chart! -> abort${NC}"
        echo -e "${YELLOW}This can be related to issues on the registry side or connection issues.${NC}"
        echo -e "${YELLOW}Retrying the deployment script might solve this issue.${NC}"
        exit 1
    fi
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
    STRIPPED_CONTAINER_REGISTRY_URL=$(echo "$CONTAINER_REGISTRY_URL" | sed -E 's~^https?://~~' | cut -d'/' -f1)

    # Build helm registry login command with optional --plain-http flag
    HELM_LOGIN_CMD="$HELM_EXECUTABLE registry login"
    if [ "$PLAIN_HTTP" = true ]; then
        HELM_LOGIN_CMD="$HELM_LOGIN_CMD --plain-http"
    fi

    $HELM_LOGIN_CMD -u $CONTAINER_REGISTRY_USERNAME -p $CONTAINER_REGISTRY_PASSWORD $(echo "$CONTAINER_REGISTRY_URL" | cut -d/ -f1)
}

function install_certs {
    if [ "$EUID" -ne 0 ]
    then echo -e "The installation of certs requires root privileges!";
        exit 1
    fi

    if [ ! -f ./tls.key ] || [ ! -f ./tls.crt ]; then
        echo -e "${RED}tls.key or tls.crt could not been found in this directory.${NC}"
        echo -e "${RED}Please rename and copy the files first!${NC}"
        exit 1
    else
        echo -e "files found!"
        echo -e "Creating cluster secret ..."
        microk8s.kubectl delete secret certificate -n $ADMIN_NAMESPACE
        microk8s.kubectl create secret tls certificate --namespace $ADMIN_NAMESPACE --key ./tls.key --cert ./tls.crt
        auth_proxy_pod=$(microk8s.kubectl get pods -n $ADMIN_NAMESPACE |grep oauth2-proxy  | awk '{print $1;}')
        echo "auth_proxy_pod pod: $auth_proxy_pod"
        microk8s.kubectl -n $ADMIN_NAMESPACE delete pod $auth_proxy_pod
        cp ./tls.key ./tls.crt $FAST_DATA_DIR/tls/
    fi

    echo -e "${GREEN}DONE${NC}"
}

function print_deployment_done {
    echo -e "${GREEN}Deployment done."
    print_resource_configs
    echo -e "Please wait till all components have been downloaded and started."
    echo -e "You can check the progress with:"
    echo -e "watch microk8s.kubectl get pods -A"
    echo -e "When all pod are in the \"running\" or \"completed\" state,${NC}"

    if [ -v DOMAIN ];then
        echo -e "${GREEN}you can visit: https://$DOMAIN:$HTTPS_PORT/"
        echo -e "You should be welcomed by the login page."
        echo -e "Initial credentials:"
        echo -e "username: kaapana"
        echo -e "password: ${KAAPANA_INIT_PASSWORD} ${NC}"
    fi
}

function print_resource_configs {
    echo "Total memory of the node: $(awk "BEGIN {printf \"%.2f\", $TOTAL_MEMORY/1024}") Gi"
    echo "Allocatable memory of the node: $(awk "BEGIN {printf \"%.2f\", $ALLOCATABLE_MEMORY/1024}") Gi"
    echo ""
    echo "PACS minimum memory request: $(awk "BEGIN {printf \"%.2f\", $PACS_MEMORY_REQUEST/1024}") Gi"
    echo "PACS maximum memory limit: $(awk "BEGIN {printf \"%.2f\", $PACS_MEMORY_LIMIT/1024}") Gi"
    echo ""
    echo "Airflow minimum memory request: $(awk "BEGIN {printf \"%.2f\", $AIRFLOW_MEMORY_REQUEST/1024}") Gi"
    echo "Airflow maximum memory limit: $(awk "BEGIN {printf \"%.2f\", $AIRFLOW_MEMORY_LIMIT/1024}") Gi"
    echo ""
    echo "Opensearch minimum memory request: $(awk "BEGIN {printf \"%.2f\", $OPENSEARCH_MEMORY_REQUEST/1024}") Gi"
    echo "Opensearch maximum memory limit: $(awk "BEGIN {printf \"%.2f\", $OPENSEARCH_MEMORY_LIMIT/1024}") Gi"
    echo ""
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
        if [ "$QUIET" = "false" ] ; then
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

function update_coredns_rewrite() {
    # Get the hostname from helm values
    local hostname=$DOMAIN # $(helm get values kaapana-platform-chart -o json | jq -r ".global.hostname")
    if [ -z "$hostname" ]; then
        echo "Error: hostname not"
        return 1
    fi

    # If hostname starts with a number it is considerd an IP and dns rewrite is skipped
    if [[ "$hostname" =~ ^[0-9] ]]; then
        echo "Skipped DNS rewrite because ${hostname} seems to be an IP Adress"
        return 0
    fi

    # Build the new rewrite rule.
    # Ensure both hostname and target are FQDNs (with trailing dots).
    local new_rule="rewrite name exact ${hostname}. oauth2-proxy-service.$ADMIN_NAMESPACE.svc.cluster.local."

    echo "Updating CoreDNS rewrite rule for hostname ${hostname}"

    # Retrieve the current CoreDNS ConfigMap and update the Corefile:
    # - Split the Corefile into lines.
    # - If a rewrite rule for our hostname exists, update it.
    # - Otherwise, insert the new rule before the first line starting with "kubernetes"
    microk8s.kubectl get configmap coredns -n kube-system -o json | jq --arg new_rule "$new_rule" --arg ns "$ADMIN_NAMESPACE"  '
    .data.Corefile |= (
        # Remove any rewrite lines for oauth2-proxy-service.<namespace>.svc.cluster.local.
        gsub("(?m)^[[:space:]]*rewrite name exact [^\\n]+ oauth2-proxy-service\\." + $ns + "\\.svc\\.cluster\\.local\\.";"") |
        split("\n") as $lines |
        ($lines | to_entries) as $entries |
        ( $entries
          | map(select(.value | test("^[[:space:]]*kubernetes ")))
          | .[0].key // ($lines | length)
        ) as $kube_index |
        ($lines[0:$kube_index] + [$new_rule] + $lines[$kube_index:]) | join("\n")
    )
    | del(.metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"])
    | del(.metadata.managedFields)
    ' > /tmp/coredns.json

    # Replace the ConfigMap entirely.
    microk8s.kubectl replace -f /tmp/coredns.json
    if [ $? -eq 0 ]; then
        echo "CoreDNS ConfigMap updated successfully."
    else
        echo "Failed to update CoreDNS ConfigMap."
        return 1
    fi

    # Restart the CoreDNS deployment to load the new configuration.
    microk8s.kubectl rollout restart deployment coredns -n kube-system
    if [ $? -eq 0 ]; then
        echo "CoreDNS deployment restarted successfully."
    else
        echo "Failed to restart CoreDNS deployment."
        return 1
    fi
}

function check_system() {
    release="$1"
    helm_ns="${2:-default}"

    # Extract all resources from the Helm manifest
    resources=$(
    $HELM_EXECUTABLE get manifest "$release" -n "$helm_ns" \
        | microk8s.kubectl apply --dry-run=client -f - -o json \
        | jq -r '.items[] | "\(.kind)/\(.metadata.namespace)/\(.metadata.name)"'
    )

    all_healthy=true

    for res in $resources; do
    kind=$(echo "$res" | cut -d'/' -f1)
    ns=$(echo "$res" | cut -d'/' -f2)
    name=$(echo "$res" | cut -d'/' -f3)

    case $kind in
        Deployment)
        if ! microk8s.kubectl rollout status "deployment/$name" -n "$ns"; then
            echo "❌ Deployment $name not healthy"
            all_healthy=false
        fi
        ;;
        StatefulSet)
        if ! microk8s.kubectl rollout status "statefulset/$name" -n "$ns"; then
            echo "❌ StatefulSet $name not healthy"
            all_healthy=false
        fi
        ;;
        Pod)
        phase=$(microk8s.kubectl get pod "$name" -n "$ns" -o jsonpath='{.status.phase}')
        if [[ "$phase" != "Running" && "$phase" != "Succeeded" ]]; then
            echo "❌ Pod $name is $phase"
            all_healthy=false
        fi
        ;;
        Job)
        succeeded=$(microk8s.kubectl get job "$name" -n "$ns" -o jsonpath='{.status.succeeded}')
        if [[ "$succeeded" != "1" ]]; then
            echo "❌ Job $name not successful"
            all_healthy=false
        fi
        ;;
        *)
        ;;
    esac
    done

    if [ "$all_healthy" = true ]; then
        echo "✅ All resources healthy"
    else
        echo "❌ Some resources are unhealthy"
        exit 1
    fi

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
echo "Version: 0.5.3-latest"
echo "Report created on $(date +'%Y-%m-%d')"

--- "Basics"
uptime
free

--- "Last 2H Log"
journalctl --since "2 hours ago"

--- "Pod Status"
microk8s.kubectl get pods -A

--- "External Internet Access"
ping -c3 -i 0.2 www.dkfz-heidelberg.de

--- "Check Registry"
openssl s_client -connect $CONTAINER_REGISTRY_URL:443

--- "Check Registry Credentials"
if [ "$PLAIN_HTTP" = true ]; then
    $HELM_EXECUTABLE registry login --plain-http -u $CONTAINER_REGISTRY_USERNAME -p $CONTAINER_REGISTRY_PASSWORD $CONTAINER_REGISTRY_URL
else
    $HELM_EXECUTABLE registry login -u $CONTAINER_REGISTRY_USERNAME -p $CONTAINER_REGISTRY_PASSWORD $CONTAINER_REGISTRY_URL
fi

--- "Systemd Status"
systemd status

--- "Kernel Modules"
lsmod

--- "Storage"
df -h

--- "Snaps"
snap list

--- "k8s Pods"
microk8s.kubectl get pods -A

--- "k8s Describe Pods"
microk8s.kubectl describe pods -A

--- "k8s Node Status"
microk8s.kubectl describe node

--- "GPU Hardware"
lshw -C Display

--- "GPU Kernel Module"
modinfo nvidia | grep ^version

--- "GPU"
nvidia-smi

--- "Resource Health"
check_system kaapana-admin-chart default
check_system kaapana-platform-chart default
check_system project-admin admin

--- "END"
}

### MAIN programme body:
main $@